## Installation
For development in the backend you need the client, `jobq`, as an editable dependency.
Install it with `uv pip install -e .` in the backend folder.
You can launch the backend with 
`uvicorn src.jobq_server.__main__:app --reload` in the backend root.
