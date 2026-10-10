# docker/vlm — a vision-language model on one GPU, for the data-sheet experiments

llama.cpp's `llama-server` built for an RTX 4090 on a host whose NVIDIA driver stops at CUDA 12.2, serving
**Qwen3.8-27B** with its vision projector through the OpenAI-compatible `/v1/chat/completions` API.
`docker/datasheets/` is what uses it.

```sh
make vlm-image                 # CUDA 12.2 base images by digest, llama.cpp at a fixed commit
make vlm-models                # the weights into $VLM_MODELS, checked by sha256 (fetch_qwen38_vl.sh)
make vlm-serve                 # container vlm-qwen on 127.0.0.1:$VLM_PORT, GPU $VLM_GPU
make vlm-stop                  # the container holds its GPU memory until stopped
```

- Every input is pinned: base images by digest in the `Dockerfile`, llama.cpp by commit, the GGUF weights
  and projector by sha256. The weights are not in the image; they are mounted read-only from
  `$VLM_MODELS`, outside the repository.
- llama.cpp, not vLLM: vLLM's images need a newer CUDA than the driver runs. The build links the driver's
  `libcuda` lazily (`-Wl,--allow-shlib-undefined`, as upstream does), because the driver only exists at
  run time.
- Thinking is switched off per request (`chat_template_kwargs: {enable_thinking: false}`): the task is
  transcription. Temperature 0 with two requests in flight is not bit-repeatable (llama.cpp batches them).
- On lola, GPU 1 is the experiments GPU; GPU 0 belongs to other people's work.
