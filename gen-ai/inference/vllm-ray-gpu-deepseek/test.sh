# Call the server using curl:
curl -X POST "http://localhost:8000/v1/chat/completions" \
        -H "Content-Type: application/json" \
        --data '{
                "model": "deepseek-ai/deepseek-coder-6.7b-instruct",
                "messages": [
                        {
                                "role": "user",
                                "content": "What is the capital of France?"
                        }
                ]
        }'
