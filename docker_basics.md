# Docker basics

Docker packages an application together with its dependencies into a container image, so it runs the same way on any machine. An image is built from a Dockerfile, which lists the base image, the files to copy and the command to run.

A container is a running instance of an image. The command docker build creates an image, and docker run starts a container from it. The flag -p maps a port on the host to a port inside the container, and -e sets an environment variable.

Secrets such as API keys should be passed to a container as environment variables at run time and must not be written into the image or committed to Git.

A .dockerignore file keeps unnecessary files, like local virtual environments, out of the build context and makes builds faster.
