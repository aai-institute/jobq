from jobs import ImageBuilder, Runner, job


@job
def my_job() -> None:
    print("Hello, world")


if __name__ == "__main__":
    # image = ImageBuilder.from_dockerfile("example:latest")
    # Runner.run(my_job, image)
    my_job()
