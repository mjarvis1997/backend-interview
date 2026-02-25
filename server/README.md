## Setup

1. **Install Poetry** (if not already installed):
https://python-poetry.org/docs/#installing-with-pipx

2. **Install dependencies**:
   ```bash
   cd server
   poetry install
   ```

3. **Run the server**:
   ```bash
   poetry run start
   ```

4. **Access the API**:
   - API: http://localhost:8000

## Docker setup
```
docker run --name mongodb -d mongo:8.2.6-rc0-noble
```

## AI In My Workflow

### Used for initial scaffolding
Project structure and package management have consistent standards and the process of initializing a new project can be tedious, so it was a good opportunity to save some time.

I did find the initial attempt pretty bloated. I took a look through the files and ended up using a clean poetry project and copied the helpful parts of the AI generated directory. It was helpful to see some modern patterns but I also compared the output with what is recommended in the docs for poetry and FastAPI.

## Docs
https://fastapi.tiangolo.com/tutorial/first-steps/

https://python-poetry.org/docs/basic-usage/

https://hub.docker.com/_/mongo

https://beanie-odm.dev/getting-started/

## References
https://github.com/roman-right/beanie-fastapi-demo

## TODO
consider pydantic
setup mongodb and some fastapi endpoints to test it