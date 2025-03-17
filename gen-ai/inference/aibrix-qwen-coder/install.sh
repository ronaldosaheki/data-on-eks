# Install component dependencies
kubectl create -f https://github.com/vllm-project/aibrix/releases/download/v0.2.1/aibrix-dependency-v0.2.1.yaml

# Install aibrix components
kubectl create -f https://github.com/vllm-project/aibrix/releases/download/v0.2.1/aibrix-core-v0.2.1.yaml
