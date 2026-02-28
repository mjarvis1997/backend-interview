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

### Run all containers

For prod and testing, run all the containers.

1. **Start all services**:
   ```bash
   docker compose --profile prod up --build
   ```

### Access services:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MongoDB: http://localhost:27017
   - Mongo Express: http://localhost:8081 (mongoexpressuser/mongoexpresspass)
   - RQ Dashboard: http://localhost:9181

## Considerations for moving to production
Because this is a proof of concept I made some concessions for ease of setup and testing. Here is a list of things I would plan to address before actually sharing or deploying this project:

- Use cloud service for secrets and env vars
- Provision non-root users for db access (current connection string is hardcoded)
- Configure env vars and docker setup to support multiple environments (local, test, stage, prod)
- Use external volume for Redis data so it would persist between restarts
- Less naive caching strategy
   - Currently it is static, in prod would prefer dynamic invalidation and TTL based on real volume (e.g. if >5% of data volume is loaded)

## Requirements checklist
### Async Event Ingestion Pipeline
This is working well. I am using RQ to manage the queue and workers, which makes convenient use of Redis for the queue and allows for easy scaling by simply adding more worker containers. The workers are able to process events asynchronously and retry on failure with a simple backoff strategy.

I was able to use RQ dashboard to monitor the queue and see the jobs being processed in real time, which was a nice bonus for visibility.

### Querying & Analytics
All of the MongoDB endpoints are implemented using Beanie, which provides a nice interface for querying and aggregation.

#### __GET /events__
For this I created a simple endpoint that accepts query parameters for filtering by:
- event type
- date range
- user ID
- source URL


#### GET /events/stats
This endpoint uses a MongoDB aggregation pipeline to return counts of events grouped by type and time bucket. The time bucket can be configured via query parameter to be hourly, daily, or weekly. I designed it to be fairly simple and flexible so that a frontend could easily filter and display the results as needed.

#### GET /events/search
TODO: 


#### GET /events/stats/realtime
This endpoint request struck me as a bit odd. For the purposes of this proof of concept, I felt the main goal was to implement some Redis caching.

In the real world, we would probably want to just implement opt-in caching on the `/events` endpoint itself. I don't see much use of a separate endpoint.

Then, if we needed a frontend dashboard that required real-time cached stats we could repeatedely use similar queries to hit the cache and keep it warm. But for now I implemented a separate endpoint that simply returns a daily count of events from the past month, and caches the results under a fixed key in Redis with a TTL that is configurable via env variables.

### Caching Strategy
Currently the caching strategy is pretty naive, it simply caches the results of the `/events/stats/realtime` endpoint under a fixed key with a TTL.

This is sufficient for a proof of concept but in production I would consider a more dynamic caching strategy that could:
- Invalidate or update cached results based on actual data changes or volume
- Use cache warming, where we proactively refresh the cache at regular intervals
- Store results more granularly, like by time bucket. This would allow subsequent queries to reuse parts of the cached results even if they are not an exact match for the cache key. For some use cases this is overkill but for others it could provide a nice balance between cache hit rate and freshness of data.

### Indexing Strategy
#### MongoDB
Here I focused on indexing the fields that are most commonly used for filtering and aggregation in the endpoints. I also thought about what a frontend user would want to filter or group by when looking at event data.
I suspect most use cases would involve filtering by a specific time range, so I created compound indexes that include the timestamp along with other commonly filtered fields. In terms of directionality, I set the timestamp to be descending in the indexes since most queries will likely be looking for recent events.

##### Indexes:
- `Timestamp + Type` (compound index):
  - The most important in my opinion
  - Supports multiple query patterns

- `User ID + Timestamp` (compound index):
  - In a CRM context it is common to query events for a given user.

- `Source URL + Timestamp` (compound index):
  - In a CRM context it is common to want to see events from a given source.

##### Intentionally not indexed in MongoDB:
While it is tempting to index all fields for optimal reads, this is a slippery slope. Each index adds overhead to writes and in this context the MongoDB's main purpose is to quickly ingest events - the more complicated filtering and searching should be offloaded to Elasticsearch.

- Full-text search indexes
- Metadata field indexes
- Individual indexes on fields that are filterable on but not commonly used by themselves.

### Architecture Document
TODO: 


### Testing
TODO:

### Code Quality & Standards
TODO: 

## AI In My Workflow

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

https://pypi.org/project/python-dotenv/

https://docs.docker.com/compose/how-tos/profiles/

https://redis.io/docs/latest/develop/clients/redis-py/

https://github.com/Parallels/rq-dashboard

https://github.com/roman-right/beanie-fastapi-demo

## TODO
core:
- Add Elasticsearch (2-3 hours)
- Create ARCHITECTURE.md (1-2 hours)
- Add Testing Suite (2-3 hours)

bonus:
- Basic rate limiting or abuse prevention middleware
- Event deduplication logic in the worker
- AWS SQS drop-in design notes — what would change if you replaced the in-process queue with real SQS?
 