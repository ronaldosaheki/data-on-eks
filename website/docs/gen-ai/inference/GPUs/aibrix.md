---
title: AiBrix on Amazon EKS
sidebar_position: 5
---
import CollapsibleContent from '../../../../src/components/CollapsibleContent';

:::caution

The **AI on EKS** content **is being migrated** to a new repository.
🔗 👉 [Read the full migration announcement »](https://awslabs.github.io/data-on-eks/docs/migration/migration-announcement)

:::

:::warning
Deployment of ML models on EKS requires access to GPUs or Neuron instances. If your deployment isn't working, it’s often due to missing access to these resources. Also, some deployment patterns rely on Karpenter autoscaling and static node groups; if nodes aren't initializing, check the logs for Karpenter or Node groups to resolve the issue.
:::

:::warning

Note: Before implementing NVIDIA NIM, please be aware it is part of [NVIDIA AI Enterprise](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/), which may introduce potential cost and licensing for production use.

For evaluation, NVIDIA also offers a free evaluation license to try NVIDIA AI Enterprise for 90 days, and you can [register](https://enterpriseproductregistration.nvidia.com/?LicType=EVAL&ProductFamily=NVAIEnterprise) it with your corporate email.
:::

:::info

We are actively enhancing this blueprint to incorporate improvements in observability, logging, and scalability aspects.
:::
# AiBrix Deployment on Amazon EKS

## Deploying

Clone the repository

```bash
git clone https://github.com/awslabs/data-on-eks.git
```

**Important Note:**

**Step1**: Ensure that you update the region in the `variables.tf` file before deploying the blueprint.
Additionally, confirm that your local region setting matches the specified region to prevent any discrepancies.

For example, set your `export AWS_DEFAULT_REGION="<REGION>"` to the desired region:


**Step2**: Run the installation script.

```bash
cd data-on-eks/ai-ml/jark-stack/terraform && chmod +x install.sh
```

```bash
./install.sh
```

### Verify the resources

Once the installation finishes, verify the Amazon EKS Cluster.

Creates k8s config file to authenticate with EKS.

```bash
aws eks --region us-west-2 update-kubeconfig --name jark-stack
```

```bash
kubectl get nodes
```

```text
NAME                                           STATUS   ROLES    AGE    VERSION
ip-100-64-118-130.us-west-2.compute.internal   Ready    <none>   3h9m   v1.30.0-eks-036c24b
ip-100-64-127-174.us-west-2.compute.internal   Ready    <none>   9h     v1.30.0-eks-036c24b
ip-100-64-132-168.us-west-2.compute.internal   Ready    <none>   9h     v1.30.0-eks-036c24b
```

Verify the NVIDIA Device plugin

```bash
kubectl get pods -n nvidia-device-plugin
```
```text
NAME                                                              READY   STATUS    RESTARTS   AGE
nvidia-device-plugin-gpu-feature-discovery-b4clk                  1/1     Running   0          3h13m
nvidia-device-plugin-node-feature-discovery-master-568b49722ldt   1/1     Running   0          9h
nvidia-device-plugin-node-feature-discovery-worker-clk9b          1/1     Running   0          3h13m
nvidia-device-plugin-node-feature-discovery-worker-cwg28          1/1     Running   0          9h
nvidia-device-plugin-node-feature-discovery-worker-ng52l          1/1     Running   0          9h
nvidia-device-plugin-p56jj                                        1/1     Running   0          3h13m
```

### Install AiBrix


https://aibrix.readthedocs.io/latest/getting_started/installation/installation.html

```bash
# Install component dependencies
kubectl create -f https://github.com/vllm-project/aibrix/releases/download/v0.2.1/aibrix-dependency-v0.2.1.yaml

# Install aibrix components
kubectl create -f https://github.com/vllm-project/aibrix/releases/download/v0.2.1/aibrix-core-v0.2.1.yaml
```

Verify AiBrix is running

```bash
kubectl get pods -n aibrix-system
```

```text
NAME                                         READY   STATUS    RESTARTS   AGE
aibrix-controller-manager-559c99fff4-t6vz9   1/1     Running   0          94s
aibrix-gateway-plugins-7745978df6-b8xqm      1/1     Running   0          94s
aibrix-gpu-optimizer-7556bb8bb7-pfdvs        1/1     Running   0          93s
aibrix-kuberay-operator-78477fc6fc-g28lm     1/1     Running   0          93s
aibrix-metadata-service-68f6448d58-9w9vl     1/1     Running   0          93s
aibrix-redis-master-85f9cff45d-c8t8x         1/1     Running   0          93s
```

### Deploy model

Create namespace

```bash
kubectl create ns aibrix
```

Create secret if you are getting model from S3:
```
export ACCESS_KEY=***
export SECRET_KEY=***
envsubst < secret.yaml | kubectl apply -n aibrix -f -
```


Deploy model
```
envsubst < base.yaml  | kubectl apply -n aibrix -f -
```


## Observability

### DCGM

Install helm package:

```bash 
helm repo add gpu-helm-charts \
  https://nvidia.github.io/dcgm-exporter/helm-charts

helm repo update

helm install \
    --set-json='image.tag="4.1.1-4.0.4-ubuntu22.04"' \
    --set-json='tolerations=[{"effect":"NoSchedule","key":"nvidia.com/gpu","operator":"Exists"}]' \
    --generate-name \
    gpu-helm-charts/dcgm-exporter
```

Create the daemonset:
```
https://raw.githubusercontent.com/NVIDIA/dcgm-exporter/master/dcgm-exporter.yaml
```

## Prometheus

```bash
cd data-on-eks/ai-ml/jark-stack/terraform/monitoring
kubectl apply -f serviceMonitor.yaml
kubectl apply -f podMonitor.yaml
```

### Grafana

- VLLM Dashboard 

Import dashboard uploading `dashboard/grafana.json`

- DCGM

Import Dashboard id: 