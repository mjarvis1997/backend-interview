## Summary
This is a simple implementation of the backend for an event tracking and analytics system. It includes:
- A FastAPI server with endpoints for ingesting events, querying events, and getting analytics
- MongoDB for event storage and aggregation
- Redis for caching analytics results and managing an async ingestion queue with RQ
- Docker setup for local development and testing
- Some monitoring tools like Mongo Express and RQ Dashboard


## Setup
The only dependency needed for both dev and prod is Docker.

https://docs.docker.com/desktop

### Run all containers

For prod and testing, run all the containers.

1. **Start all services**:
   ```bash
   docker compose --profile prod up --build
   ```


### Local Development

For development, run the FastApi server directly and use Docker for the rest.

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

### Access services:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MongoDB: http://localhost:27017
   - Redis: http://localhost:6379 (no built in UI)
   - Elasticsearch: http://localhost:9200
   - Mongo Express: http://localhost:8081 (mongoexpressuser/mongoexpresspass)
   - RQ Dashboard: http://localhost:9181

### Test the endpoints
Can use the API docs at http://localhost:8000/docs or the sample HTTP files in `app/sample-requests` for quick testing within vscode.


## Endpoint documentation
Generic documentation and testing is available in the API docs at http://localhost:8000/docs once the server is running. HTTP files in `app/sample-requests` can be used for quick testing within vscode.

#### __GET /events__
This endpoint directly queries MongoDB with the provided filters and returns matching events. I created a simple endpoint that accepts query parameters for filtering by:
- event type
- date range
- user ID
- source URL

#### __GET /events/stats__
This endpoint uses a MongoDB aggregation pipeline to return counts of events grouped by type and time bucket. The time bucket can be configured via query parameter to be hourly, daily, or weekly. I designed it to be fairly simple and flexible so that a frontend could easily filter and display the results as needed.

#### __GET /events/search__
This endpoint performs a full-text search across event metadata using Elasticsearch. It accepts a query string and optional filters for event type and date range. The results are limited to a default of 20 to focus on the most relevent matches, but this is configurable via query parameter.

#### __GET /events/stats/realtime__
This endpoint request struck me as a bit odd. For the purposes of this proof of concept, I felt the main goal was to implement some Redis caching.

In the real world, we would probably want to just implement opt-in caching on the `/events` endpoint itself. Then, if we needed a frontend dashboard that required real-time cached stats we could repeatedely use similar queries to hit the cache and keep it warm. But for now I implemented a separate endpoint that simply returns an hourly count of events from the past week, and caches the results under a fixed key in Redis with a TTL that is configurable via env variables.

#### __POST /events__
This endpoint accepts event data, validates it, and enqueues it for async processing by the workers. The workers will then write the events to MongoDB and index them in Elasticsearch. If processing fails, the job will be retried with a basic backoff strategy provided by RQ. If it fails repeatedly it will end up in a simple dead letter queue that comes implicitly with the RQ implementation.


## AI In My Workflow
In general, my strategy with AI on this project was to use it as a brainstorming partner and for scaffolding, but to rely on my own judgement and research for the actual implementation details. I found that the AI was particularly helpful for generating ideas and providing initial code snippets, but I often had to push back on or modify its suggestions based on my own understanding of the problem and the technologies involved. I used Github Copilot with Claude 4.5 Sonnet within VSCode, leveraging the autocomplete, ask, and agent features.

Below I included some specific examples of how I used AI in my workflow, as well as where I pushed back on its output.

### Used for initial scaffolding
Project structure and package management have consistent standards and the process of initializing a new project can be tedious, so it was a good opportunity to save some time.

I did find the initial attempt pretty bloated, for proof of concepts I prefer to avoid adding boilerplate for the sake of it and try to only include what is truly necessary. I took a look through the files and ended up using a clean poetry project and copied the helpful parts of the AI generated directory. It was helpful to see some modern patterns but mostly I relied on the documentation for FastApi. 

### Brainstorming Docker strategy
I was uncertain about the best way to Dockerize the python part of this backend. I did some googling and chatted with Claude about this to arrive at the conclusions below.

Claude had a pretty good first attempt at generating the Dockerfile but I did not like that it required me to run `poetry export` locally everytime I added a dependency, so I instructed it to include the `requirements.txt` generation as part of the Dockerfile. This was one of those fun moments where the LLM turned around and said hey! You're right! That is a much better solution.

> Is it worthwhile to dockerize while doing local development?

Definitely good arguments on both sides of this. Using docker means:

pros:
- more consistent outcomes across different machines
- simpler start up commands (just `compose up`)

cons: 
- slower hot reloading
- more complicated configuration requiring volumes or devcontainers

Personally my main concern is keeping local development fast and straightforward, which led me to pick a middle ground. Provide instructions for building the python server directly for local development, but set it up with a Dockerfile that we can use for testing or deployment.

> Should we use venv? Just directly install dependencies?

Docker provides isolation inherently, it's a bit redundant to spin up a venv inside the image. The argument for using `venv` within the image is that it would more closely mimic the local setup and potentially have less inconsistencies when deploying.

> Should we use `poetry run` or handle `venv` creation and use python directly?

You could use `poetry` to run within the container but for the most part it seems like unneccessary bloat. Because we are not using `venv` within the image `poetry`'s usefuleness is pretty minimal outside of keeping track of requirements.

### Asynchronous background workers
I initially had a few different ideas for this - unsure of how heavy the implemenation should be and what exact mechanism to use for the queue itself. I asked Claude for some input and it recommended a few options, one of which was to use Redis for the queue itself, which seemed perfect to me because there is already a requirement to use it for caching. I did some investigating online and found RQ, a python library intended for this exact purpose. Claude offered to hand-roll queueing management functions but for this proof of concept it seemed better to leverage an existing solution.

## Db connections for workers
I had setup `beanie` to handle interacting with the db which worked well, but ran into an issue when I started spinning up workers. They simply run the python function they have been passed, which by default doesn't have a db connection. 

My first thought was to init a pool of connections to reuse between workers, but after discussing with Claude I decided to just wrap the db connection logic in a function and let the workers individually setup a connection. A pool maybe could be better in production contexts if the constant connecting/reconnecting became an issue but there is a nice simplicity to the non-centralzied approach which allows workers to function without much scaffolding or codependency.

Pushback:
- Claude used a different async connection client instead of the currently installed one
- Claude had outdated info about RQ's support for async tasks
   - It initially created `sync` wrappers for all of the worker functions because it did not think RQ supported `async` functions, this struck me as odd.
   - I found an issue on RQ's github page about this where they noted that while the caller must be synchronous, the workers themselves are fully capable of handling async function calls
   - Claude was able to cleanup the wrapper and remove the bloat after being asked

## Docs
https://fastapi.tiangolo.com/tutorial/first-steps/

https://python-poetry.org/docs/basic-usage/

https://hub.docker.com/_/mongo

https://beanie-odm.dev/getting-started/

https://beanie-odm.dev/tutorial/aggregation/

https://github.com/roman-right/beanie-fastapi-demo

https://pypi.org/project/python-dotenv/

https://docs.docker.com/compose/how-tos/profiles/

https://redis.io/docs/latest/develop/clients/redis-py/

https://github.com/Parallels/rq-dashboard

https://www.elastic.co/docs/solutions/search

 