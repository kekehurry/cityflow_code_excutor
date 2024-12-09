# Build with Docker

- build the docker image

  `docker build --no-cache -t kekehurry/cityflow_executor .`

- create a docker container and run

```
docker run --privileged  -itd --rm \
-v /var/run/docker.sock:/var/run/docker.sock \
-v $PWD/code:/workspace/code \
-p 8000:8000 \
--env-file .env \
--name cityflow_executor \
kekehurry/cityflow_executor
```
