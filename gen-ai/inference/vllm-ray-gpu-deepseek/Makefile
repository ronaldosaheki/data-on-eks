CHART_PATH ?= charts/vllm-ray
include .env
export

install:
	helm upgrade --install deepseek-lora $(CHART_PATH) \
	  --namespace rayserve-vllm \
	  --create-namespace \
	  --set huggingface.token=$$HUGGING_FACE_HUB_TOKEN
template:
	helm template deepseek-lora $(CHART_PATH) \
	  --namespace rayserve-vllm \
	  --create-namespace \
	  --set huggingface.token=$$HUGGING_FACE_HUB_TOKEN
install:
	helm uninstall deepseek-lora $(CHART_PATH)
