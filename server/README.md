## Setup

### Local Development
1. **Install Docker**

1. **Build and run necessary containers**
   ```bash
   docker-compose up --build
   ```

1. **Install Poetry** (if not already installed):
https://python-poetry.org/docs/#installing-with-pipx

1. **Install dependencies**:
   ```bash
   cd server
   poetry install
   ```

1. **Run the server**:
   ```bash
   poetry run uvicorn app.main:app --reload --port 8000
   ```

1. **Access the API**:
   - API: http://localhost:8000

### Docker Setup

1. **Start all services** (FastAPI + MongoDB + Mongo Express):
   ```bash
   docker compose --profile prod up --build
   ```

2. **Access services**:
   - API: http://localhost:8000
   - MongoDB: localhost:27017
   - Mongo Express: http://localhost:8081 (mongoexpressuser/mongoexpresspass)

The Dockerfile automatically generates requirements.txt from your Poetry configuration, so you don't need to manually export dependencies.

## Considerations for moving to production
Because this is a proof of concept I made some concessions for ease of setup and testing. Here is a list of things I would plan to address before actually sharing or deploying this project:

- Remove env vars from git history
- Provision non-root users for db access
- Configure env vars and docker setup to support multiple environments (local, test, stage, prod)
- Use external volume for Redis data so it would persist between restarts

## AI In My Workflow

### Used for initial scaffolding
Project structure and package management have consistent standards and the process of initializing a new project can be tedious, so it was a good opportunity to save some time.

I did find the initial attempt pretty bloated, for proof of concepts I prefer to avoid adding boilerplate for the sake of it and try to only include what is truly necessary. I took a look through the files and ended up using a clean poetry project and copied the helpful parts of the AI generated directory. It was helpful to see some modern patterns but mostly I relied on the documentation for FastApi. 

### Brainstorming Docker strategy
I had some questions about the best way to Dockerize the python part of this backend. I did some googling and chatted with Claude about this to arrive at the conclusions below.

Claude had a pretty good first attempt at generating the Dockerfile but I did not like that it required me to run `poetry export` locally everytime I added a dependency, so I instructed it to include the `requirements.txt` generation as part of the Dockerfile. This was one of those fun moments where the LLM turned around and said hey! You're right! That is a much better solution.

> Is it worthwhile to dockerize while doing local development?

Definitely good arguments on both sides of this. Using docker means more consistent outcomes across different machines and makes startup simpler (just `compose up`). But it does mean the developer make hot-reloading slower and more complicated, and also means devs would need to configure containerization features within their IDE or we would need volumes to allow code changes on the machine itself to propogate to the docker image.

Personally my main concern is keeping local development fast and straightforward, which led me to pick a middle ground. Provide instructions for building the python server directly for local development, but set it up with a Dockerfile that we can use for testing or deployment.


> Should we use venv? Just directly install dependencies?

Docker provides isolation inherently, it's a bit redundant to spin up a venv inside the image. The argument for using `venv` within the image is that it would more closely mimic the local setup and potentially have less inconsistencies when deploying.
> Should we use `poetry run` or handle `venv` creation and use `python3` directly?

You could use `poetry` to run within the container but for the most part it seems like unneccessary bloat. Because we are not using `venv` within the image `poetry`'s usefuleness is pretty minimal.

### Asynchronous background workers
I initially had a few different ideas for this - unsure of how heavy the implemenation should be and what exact mechanism to use for the queue itself. I asked Claude for some input and it recommended a few options, one of which was to use Redis for the queue itself, which seemed perfect to me because there is already a requirement to use it for caching. I did some investigating online and found RQ, a python library intended for this exact purpose. Claude offered to hand-roll queueing management functions but for this proof of concept it seemed better to leverage an existing solution.

## Docs
https://fastapi.tiangolo.com/tutorial/first-steps/

https://python-poetry.org/docs/basic-usage/

https://hub.docker.com/_/mongo

https://beanie-odm.dev/getting-started/

https://pypi.org/project/python-dotenv/

https://docs.docker.com/compose/how-tos/profiles/

https://redis.io/docs/latest/develop/clients/redis-py/

## References
https://github.com/roman-right/beanie-fastapi-demo

## TODO
instead of directly storing event, enqueue the task using RQ
handle deadletter queue
look into rq dashboard