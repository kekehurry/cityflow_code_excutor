# Build with Docker

- build the docker image

	`docker build -t cityflow-python-executor .`

- create a docker container and run

	` 
    docker run --privileged \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v your_path_to_code_dir:/workspace/code \
    -e BIND_DIR="your_path_to_code_dir" \
    -p 8000:8000 \
    --name cityflow-python-executor \
    --rm \
    cityflow-python-executor
    `