
import os
import subprocess
import logging
from typing import Dict, List, Optional


from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import StreamingResponse, JSONResponse

from ray import serve
from ray.serve import Application

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.engine.async_llm_engine import AsyncLLMEngine
from vllm.entrypoints.openai.protocol import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
)
from vllm.entrypoints.openai.serving_chat import OpenAIServingChat
from vllm.entrypoints.openai.serving_models import (
    OpenAIServingModels,
    BaseModelPath,
    LoRAModulePath,
)

from vllm.config import ModelConfig
from vllm.logger import init_logger
from vllm.lora.request import LoRARequest

logger = init_logger(__name__)

# Initialize FastAPI correctly
app = FastAPI()

@serve.deployment(name="VLLMDeployment", health_check_period_s=10)
@serve.ingress(app)
class VLLMDeployment:
    def __init__(
        self,
        model: str,
        tensor_parallel_size: int,
        max_num_seqs: int,
        block_size: int,
        max_model_len: int,
        response_role: str = "assistant",
        chat_template: Optional[str] = None,
        lora_modules: Optional[List[LoRAModulePath]] = None,
    ):
        logger.info("VLLMDeployment is initializing...")

        self.model_config = ModelConfig(
            model=model,
            task="generate",  # Corrected to match supported tasks
            tokenizer=model,  # Use same model path for tokenizer
            tokenizer_mode="auto",  # Default to 'auto'
            trust_remote_code=True,  # Trust remote code for custom models
            dtype="bfloat16",  # Use model default torch_dtype=bfloat16
            seed=42,  # Default seed value
            max_model_len=max_model_len,  # Already provided
        )

        self.lora_modules = lora_modules

        self.models = OpenAIServingModels(
            engine_client=None,  # Ensure it initializes later
            model_config=self.model_config,
            base_model_paths=[BaseModelPath(name=model, model_path=model)],
            lora_modules=self.lora_modules,
        )

        # Initialize VLLM Engine
        engine_args = AsyncEngineArgs(
            model=model,
            tensor_parallel_size=tensor_parallel_size,
            max_num_seqs=max_num_seqs,
            block_size=block_size,
            max_model_len=max_model_len,
            disable_log_requests=True,
            device="cuda",
            dtype="bfloat16",  # Matches model config
            trust_remote_code=True,
            enable_lora=True,
            max_loras=1,
            max_lora_rank=8,
        )
        logger.info(f"Engine Args Initialized: {engine_args}")

        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.response_role = response_role
        self.chat_template = chat_template
        self.openai_serving_chat = None

    async def health_check(self):
        """Health check for Ray Serve deployment"""
        logger.info("Health check passed for VLLMDeployment.")
        return "OK"

    @app.get("/v1/models")
    async def get_models(self):
        """List available models in OpenAI format."""
        return JSONResponse(
            content={
                "object": "list",
                "data": [
                    {
                        "id": self.model_config.model,
                        "object": "model",
                        "owned_by": "organization",
                        "permission": [],
                    }
                ],
            }
        )

    @app.post("/v1/chat/completions")
    async def create_chat_completion(
        self, request: ChatCompletionRequest, raw_request: Request
    ):
        """Handle chat requests with OpenAI-compatible response format."""
        if not self.openai_serving_chat:
            logger.info("Initializing OpenAIServingChat instance...")

            self.openai_serving_chat = OpenAIServingChat(
                engine_client=self.engine,
                model_config=self.model_config,
                models=self.models,
                response_role=self.response_role,
                request_logger=None,
                chat_template=self.chat_template,
                chat_template_content_format="default",
                return_tokens_as_token_ids=False,
                enable_auto_tools=False,
                tool_parser=None,
                enable_prompt_tokens_details=False,
            )

        logger.info(f" Received request: {request}")
        generator = await self.openai_serving_chat.create_chat_completion(request, raw_request)

        if isinstance(generator, ErrorResponse):
            return JSONResponse(content=generator.model_dump(), status_code=generator.code)

        if request.stream:
            return StreamingResponse(content=generator, media_type="text/event-stream")
        else:
            assert isinstance(generator, ChatCompletionResponse)
            return JSONResponse(content=generator.model_dump())

def app_builder(args: Dict[str, str]) -> Application:
    return VLLMDeployment.bind(
        model=os.environ.get('MODEL_ID', 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B'),
        tensor_parallel_size=int(os.environ.get('TENSOR_PARALLEL_SIZE', '1')),
        max_num_seqs=int(os.environ.get('MAX_NUM_SEQS', '32')),
        block_size=int(os.environ.get('BLOCK_SIZE', '4096')),
        max_model_len=int(os.environ.get('MAX_MODEL_LEN', '8192')),
      )