# GEMINI.md: Project Overview and Development Guide

## Project Overview

This project is the **Pyramid RAG Platform**, an enterprise-grade, on-premise retrieval-augmented generation (RAG) platform. It enables users to upload, search, and query company documents using an AI assistant.

### Main Technologies

*   **Backend:** Python with FastAPI
*   **Frontend:** React with TypeScript and Material-UI
*   **Database:** PostgreSQL with the `pgvector` extension for semantic search
*   **LLM Engine:** Qwen 2.5 14B served via Ollama, with GPU acceleration
*   **Document Processing:** Celery for asynchronous task handling
*   **Orchestration:** Docker and Docker Compose
*   **Monitoring:** Prometheus and Grafana

### Architecture

The system is composed of several microservices orchestrated by Docker Compose:

*   **`frontend`**: A React-based user interface.
*   **`nginx`**: A reverse proxy that routes traffic to the frontend and backend services.
*   **`backend`**: A FastAPI application that provides the core business logic and API.
*   **`postgres`**: A PostgreSQL database for storing metadata and vector embeddings.
*   **`redis`**: A Redis instance for caching and as a message broker for Celery.
*   **`celery-worker`**: A Celery worker that processes documents asynchronously.
*   **`celery-beat`**: A Celery scheduler for periodic tasks.
*   **`ollama`**: The service that runs the large language model.
*   **`prometheus`**: A service for collecting metrics.
*   **`grafana`**: A service for visualizing metrics.

## Building and Running

The project is designed to be run with Docker and Docker Compose.

### Prerequisites

*   Docker
*   Docker Compose
*   NVIDIA Container Toolkit (for GPU support)

### Setup and Execution

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/pyramid-computer/pyramid-rag.git
    cd pyramid-rag
    ```

2.  **Run the setup script:**
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    This script will:
    *   Check for dependencies.
    *   Create configuration files.
    *   Download Docker images.
    *   Start all services.
    *   Pull the required LLM model.

3.  **Access the application:**
    *   **Main Application:** [http://localhost](http://localhost)
    *   **Admin Login:** `admin@pyramid-computer.de` / `PyramidAdmin2024!`
    *   **Grafana:** [http://localhost:3001](http://localhost:3001) (admin/admin)
    *   **Prometheus:** [http://localhost:9090](http://localhost:9090)
    *   **Flower (Celery Monitor):** [http://localhost:5555](http://localhost:5555)
    *   **API Docs (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

### Key `docker-compose` commands:

*   **Start all services:** `docker-compose up -d`
*   **Stop all services:** `docker-compose down`
*   **View logs:** `docker-compose logs -f [service_name]`
*   **Rebuild and restart:** `docker-compose up -d --build`

## Development Conventions

### Backend (Python/FastAPI)

*   **Dependency Management:** `pip` and `requirements.txt`.
*   **Code Style:** `black` for formatting, `flake8` for linting, and `mypy` for type checking.
*   **Testing:** `pytest` is used for unit and integration tests.
*   **Database Migrations:** `alembic` is used for managing database schema changes.
*   **Environment Variables:** Configuration is managed through a `.env` file.

### Frontend (React/TypeScript)

*   **Dependency Management:** `npm`.
*   **Build Tool:** `vite`.
*   **Code Style:** `prettier` for formatting and `eslint` for linting.
*   **Testing:** `vitest` and `react-testing-library`.
*   **UI Framework:** Material-UI (MUI).
*   **State Management:** Redux Toolkit.
*   **Data Fetching:** React Query and Axios.

### Key `npm` scripts (run from the `frontend` directory):

*   **Start development server:** `npm run dev`
*   **Build for production:** `npm run build`
*   **Run tests:** `npm run test`
*   **Lint and format:** `npm run lint` and `npm run format`

# Detailed Code Documentation

## Backend

### File: `C:\AI\pyramid-rag\backend\test_pdf_pipeline.py`

*   **Class: `TestPDFProcessingPipeline(unittest.TestCase)`**
    *   **Description:** This class contains unit tests for the PDF processing pipeline. It uses mocking to isolate the components under test.
    *   **Location:** `C:\AI\pyramid-rag\backend\test_pdf_pipeline.py`
    *   **Methods:**
        *   `test_pdf_to_chunks(self, mock_get_encoding, mock_pdf_reader)`: Tests the splitting of a PDF document into text chunks. It mocks the PDF reader and the token encoder.
        *   `test_process_pdf_integration(self, mock_pdf_reader)`: An integration test for processing a PDF file. It mocks the PDF reader.

### File: `C:\AI\pyramid-rag\backend\app\services\document_processor.py`

*   **Class: `TextSplitter`**
    *   **Description:** A utility class for splitting text into chunks based on token count. It uses a `RecursiveCharacterTextSplitter` from `langchain` and `tiktoken` for token counting.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\document_processor.py`
    *   **Methods:**
        *   `__init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, model_name: str = "gpt-3.5-turbo")`: Initializes the text splitter with a specific chunk size, overlap, and model for tokenization.
        *   `split_text(self, text: str) -> List[str]`: Splits the given text into chunks.

*   **Class: `DocumentProcessor`**
    *   **Description:** This class is responsible for processing different document types (PDF, text) and extracting their content.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\document_processor.py`
    *   **Methods:**
        *   `__init__(self, chunk_size: int = 1000, chunk_overlap: int = 200)`: Initializes the document processor, setting up the text splitter.
        *   `process_pdf(self, file_path: str) -> Tuple[str, int]`: Reads a PDF file, extracts its text content, and returns the content along with the page count.
        *   `process_text(self, text: str) -> str`: Cleans and processes a raw text string.
        *   `process_document(self, file_path: str) -> Tuple[str, int]`: Detects the document type based on the file extension and uses the appropriate method to process it. It currently supports `.pdf` and `.txt` files.

### File: `C:\AI\pyramid-rag\backend\app\mcp_network_server.py`

*   **Class: `MCPNetworkServer`**
    *   **Description:** A network server for the MCP (Model-Controller-Processor) architecture. It listens for incoming connections on a specified host and port, receives messages, processes them using a `ToolProcessor`, and sends back the results. The communication protocol uses a simple header to indicate the length of the message.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\mcp_network_server.py`
    *   **Methods:**
        *   `__init__(self, host='127.0.0.1', port=8765)`: Initializes the server with a host and port.
        *   `handle_client(self, client_socket)`: Handles a single client connection. It reads the message, processes it, and sends the response.
        *   `start(self)`: Starts the server, listens for connections, and handles them in separate threads.

### File: `C:\AI\pyramid-rag\backend\app\main.py`

*   **FastAPI app setup**
    *   **Description:** This section of the code initializes the FastAPI application. It includes CORS middleware to allow cross-origin requests from the frontend. It also mounts a static directory for serving uploaded files.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\main.py`
*   **Routers**
    *   **Description:** The API routers for different parts of the application are included here. This organizes the endpoints into logical groups. It includes routers for `auth`, `users`, `documents`, `chat`, and `admin`.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\main.py`
*   **Event Handlers**
    *   **`startup_event()`**: 
        *   **Description:** An asynchronous function that runs on application startup. It can be used to initialize resources like database connections.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\main.py`
*   **Root Endpoint**
    *   **`read_root()`**: 
        *   **Description:** A simple root endpoint that returns a welcome message.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\main.py`

### File: `C:\AI\pyramid-rag\backend\app\services\upload_response.py`

*   **Class: `UploadResponse`**
    *   **Description:** A class to generate structured JSON responses for file uploads. It provides methods to add details about the uploaded file, extracted text, and any errors that occurred.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\upload_response.py`
    *   **Methods:**
        *   `__init__(self, file_path: str)`: Initializes the response with the path to the uploaded file.
        *   `set_text(self, text: str, page_count: int = 0)`: Sets the extracted text and page count.
        *   `set_error(self, error_message: str)`: Sets an error message if the upload failed.
        *   `to_json(self)`: Returns the structured response as a JSON string.

### File: `C:\AI\pyramid-rag\backend\app\services\text_utils.py`

*   **Functions:**
    *   `estimate_token_count(text: str, model_name: str = "gpt-3.5-turbo") -> int`:
        *   **Description:** Estimates the number of tokens in a given text using `tiktoken`.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\services\text_utils.py`
    *   `clean_text(text: str) -> str`:
        *   **Description:** Cleans a text string by removing extra whitespace and non-printable characters.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\services\text_utils.py`

### File: `C:\AI\pyramid-rag\backend\test_upload_response.py`

*   **Class: `TestUploadResponse(unittest.TestCase)`**
    *   **Description:** Contains unit tests for the `UploadResponse` class to ensure it generates correct JSON responses.
    *   **Location:** `C:\AI\pyramid-rag\backend\test_upload_response.py`
    *   **Methods:**
        *   `test_success_response()`: Tests the successful creation of a JSON response for a file upload.
        *   `test_error_response()`: Tests the creation of an error response.

### File: `C:\AI\pyramid-rag\backend\app\schemas.py`

*   **Pydantic Models:**
    *   **`UserCreate`**: Schema for user creation.
    *   **`User`**: Schema for representing a user.
    *   **`Token`**: Schema for the authentication token.
    *   **`TokenData`**: Schema for the data encoded in the token.
    *   **`Document`**: Schema for a document.
    *   **`ChatMessage`**: Schema for a chat message.
    *   **`Chat`**: Schema for a chat session.
    *   **`SearchResult`**: Schema for a search result.
    *   **Description:** These Pydantic models define the structure of the data exchanged with the API. They are used by FastAPI for request and response validation, and for generating the OpenAPI documentation.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\schemas.py`

### File: `C:\AI\pyramid-rag\backend\app\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `app` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\api\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `api` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\api\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\api\deps.py`

*   **Functions:**
    *   `get_db()`:
        *   **Description:** A dependency that provides a database session. It ensures that the database session is properly closed after the request is finished.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\deps.py`
    *   `get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> models.User`:
        *   **Description:** A dependency that gets the current authenticated user from the provided JWT token. It decodes the token, retrieves the user from the database, and returns the user object.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\deps.py`
    *   `get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User`:
        *   **Description:** A dependency that checks if the current user is active. It's built on top of `get_current_user`.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\deps.py`
    *   `get_current_active_superuser(current_user: models.User = Depends(get_current_user)) -> models.User`:
        *   **Description:** A dependency that checks if the current user is a superuser.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\deps.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `endpoints` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\admin.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `get_server_status(db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_active_superuser)) `:
        *   **Description:** An endpoint to get the status of the server, including database connection status and other checks. Requires superuser privileges.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\admin.py`
    *   `get_celery_worker_status(current_user: models.User = Depends(deps.get_current_active_superuser)) `:
        *   **Description:** An endpoint to get the status of the Celery workers. Requires superuser privileges.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\admin.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\auth.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `login_for_access_token(db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()) -> schemas.Token`:
        *   **Description:** The main login endpoint. It takes a username and password, authenticates the user, and returns a JWT access token.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\auth.py`
    *   `test_token(current_user: models.User = Depends(deps.get_current_user)) `:
        *   **Description:** A test endpoint to check if a token is valid. It returns the current user if the token is valid.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\auth.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\chat.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `chat_endpoint(chat_message: schemas.ChatMessage, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) `:
        *   **Description:** The main chat endpoint. It receives a chat message, processes it (potentially using RAG), and returns a response from the language model.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\chat.py`
    *   `stream_chat_endpoint(chat_message: schemas.ChatMessage, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) -> StreamingResponse`:
        *   **Description:** A chat endpoint that streams the response from the language model back to the client.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\chat.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\documents.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `upload_document(file: UploadFile = File(...), db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) `:
        *   **Description:** An endpoint for uploading documents. It saves the file, creates a document record in the database, and triggers a background task to process the document.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\documents.py`
    *   `get_documents(db: Session = Depends(deps.get_db), skip: int = 0, limit: int = 100, current_user: models.User = Depends(deps.get_current_user)) -> List[schemas.Document]`:
        *   **Description:** An endpoint to retrieve a list of documents.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\documents.py`
    *   `get_document(document_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) -> schemas.Document`:
        *   **Description:** An endpoint to retrieve a single document by its ID.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\documents.py`
    *   `delete_document(document_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) `:
        *   **Description:** An endpoint to delete a document.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\documents.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\search.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `search_documents(query: str, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_user)) -> List[schemas.SearchResult]`:
        *   **Description:** An endpoint to perform a semantic search over the documents in the vector store.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\search.py`

### File: `C:\AI\pyramid-rag\backend\app\api\endpoints\users.py`

*   **Router:** `router = APIRouter()`
*   **Endpoints:**
    *   `create_user(user: schemas.UserCreate, db: Session = Depends(deps.get_db)) -> schemas.User`:
        *   **Description:** An endpoint to create a new user.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\users.py`
    *   `read_users(skip: int = 0, limit: int = 100, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_active_superuser)) -> List[schemas.User]`:
        *   **Description:** An endpoint to read a list of users. Requires superuser privileges.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\users.py`
    *   `read_user(user_id: int, db: Session = Depends(deps.get_db), current_user: models.User = Depends(deps.get_current_active_superuser)) -> schemas.User`:
        *   **Description:** An endpoint to read a single user by ID. Requires superuser privileges.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\api\endpoints\users.py`

### File: `C:\AI\pyramid-rag\backend\app\auth.py`

*   **Functions:**
    *   `verify_password(plain_password: str, hashed_password: str) -> bool`:
        *   **Description:** Verifies a plain-text password against a hashed password.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\auth.py`
    *   `get_password_hash(password: str) -> str`:
        *   **Description:** Hashes a plain-text password.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\auth.py`
    *   `create_access_token(data: dict, expires_delta: timedelta | None = None) -> str`:
        *   **Description:** Creates a JWT access token.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\auth.py`
    *   `authenticate_user(db: Session, username: str, password: str) -> models.User | None`:
        *   **Description:** Authenticates a user by username and password.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\auth.py`

### File: `C:\AI\pyramid-rag\backend\app\database.py`

*   **Database Setup:**
    *   **Description:** This file configures the SQLAlchemy database engine and session management. It reads the database URL from the environment variables and creates a `SessionLocal` class to handle database sessions. It also defines a `Base` class for the declarative ORM models.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\database.py`

### File: `C:\AI\pyramid-rag\backend\app\embeddings_service.py`

*   **Class: `EmbeddingService`**
    *   **Description:** A service class for generating embeddings for text. It uses a sentence-transformer model to create vector embeddings.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\embeddings_service.py`
    *   **Methods:**
        *   `__init__(self, model_name: str = 'all-MiniLM-L6-v2')`: Initializes the embedding service with a specified model.
        *   `get_embedding(self, text: str) -> List[float]`: Generates an embedding for a single piece of text.
        *   `get_embeddings(self, texts: List[str]) -> List[List[float]]`: Generates embeddings for a list of texts.

### File: `C:\AI\pyramid-rag\backend\app\main_minimal.py`

*   **Description:** A minimal version of the FastAPI application, likely used for testing or a lightweight deployment. It includes a basic chat endpoint.
*   **Location:** `C:\AI\pyramid-rag\backend\app\main_minimal.py`
*   **Endpoints:**
    *   `chat(message: str)`: A simple chat endpoint that takes a message and returns a hardcoded response.

### File: `C:\AI\pyramid-rag\backend\app\mcp_server_stdio.py`

*   **Class: `MCPServerStdio`**
    *   **Description:** A server for the MCP architecture that uses standard input/output for communication. It reads messages from stdin, processes them, and writes the response to stdout.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\mcp_server_stdio.py`
    *   **Methods:**
        *   `__init__(self)`: Initializes the server.
        *   `run(self)`: Starts the server's main loop to read from stdin and process messages.

### File: `C:\AI\pyramid-rag\backend\app\mcp_server.py`

*   **Class: `ToolProcessor`**
    *   **Description:** A class that processes tool calls specified in a JSON message. It dynamically calls methods on a `ToolRegistry` class based on the message content.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\mcp_server.py`
    *   **Methods:**
        *   `process(self, message_json: str) -> str`: Processes a JSON message containing a tool call and returns the result.
*   **Class: `ToolRegistry`**
    *   **Description:** A placeholder class for registering and executing tools.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\mcp_server.py`
    *   **Methods:**
        *   `execute_tool(self, tool_name: str, **kwargs)`: A placeholder method for executing a tool.

### File: `C:\AI\pyramid-rag\backend\app\mcp_subprocess.py`

*   **Class: `MCPSubprocess`**
    *   **Description:** A class to manage the MCP server as a subprocess. It can start, stop, and communicate with the server.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\mcp_subprocess.py`
    *   **Methods:**
        *   `__init__(self, host='127.0.0.1', port=8765)`: Initializes the subprocess manager.
        *   `start(self)`: Starts the MCP server as a subprocess.
        *   `stop(self)`: Stops the MCP server subprocess.
        *   `send_message(self, message: dict) -> dict`: Sends a message to the MCP server and returns the response.

### File: `C:\AI\pyramid-rag\backend\app\models.py`

*   **SQLAlchemy Models:**
    *   **`User`**: The ORM model for a user.
    *   **`Document`**: The ORM model for a document.
    *   **`DocumentChunk`**: The ORM model for a chunk of a document.
    *   **`Chat`**: The ORM model for a chat session.
    *   **`ChatMessage`**: The ORM model for a chat message.
    *   **Description:** These are the SQLAlchemy ORM models that define the database tables and their relationships.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\models.py`

### File: `C:\AI\pyramid-rag\backend\app\ollama_client.py`

*   **Class: `OllamaClient`**
    *   **Description:** A client for interacting with the Ollama service. It provides methods for chat and streaming chat.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\ollama_client.py`
    *   **Methods:**
        *   `__init__(self, host: str = "http://localhost:11434")`: Initializes the client with the Ollama host.
        *   `chat(self, model: str, messages: List[dict]) -> dict`: Sends a chat request to the Ollama model and returns the response.
        *   `stream_chat(self, model: str, messages: List[dict])`: Sends a chat request and streams the response.

### File: `C:\AI\pyramid-rag\backend\app\ollama_helper.py`

*   **Class: `OllamaHelper`**
    *   **Description:** A helper class that simplifies interaction with the Ollama service, adding features like RAG.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\ollama_helper.py`
    *   **Methods:**
        *   `__init__(self, ollama_client: OllamaClient, vector_store: VectorStore)`: Initializes the helper with an Ollama client and a vector store.
        *   `get_relevant_documents(self, query: str) -> List[str]`: Retrieves relevant document chunks from the vector store for a given query.
        *   `chat_with_rag(self, query: str, model: str) -> str`: Performs a chat with RAG, augmenting the user's query with relevant documents.
        *   `stream_chat_with_rag(self, query: str, model: str)`: Streams a chat response with RAG.

### File: `C:\AI\pyramid-rag\backend\app\ollama_simple.py`

*   **Functions:**
    *   `generate_response(prompt: str) -> str`:
        *   **Description:** A simple function to generate a response from the Ollama model.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\ollama_simple.py`

### File: `C:\AI\pyramid-rag\backend\app\services\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `services` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\services\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\services\embedding_service.py`

*   **Class: `EmbeddingService`**
    *   **Description:** A service for creating text embeddings using a sentence-transformer model.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\embedding_service.py`
    *   **Methods:**
        *   `__init__(self, model_name: str = 'all-MiniLM-L6-v2')`: Initializes the service with a model.
        *   `create_embeddings(self, texts: List[str]) -> List[List[float]]`: Creates embeddings for a list of texts.

### File: `C:\AI\pyramid-rag\backend\app\services\llm_service.py`

*   **Class: `LLMService`**
    *   **Description:** A service for interacting with the language model. It can use either a direct Ollama client or a RAG-enabled helper.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\llm_service.py`
    *   **Methods:**
        *   `__init__(self, use_rag: bool = True)`: Initializes the service, setting up the Ollama client and RAG helper.
        *   `chat(self, query: str) -> str`: Sends a query to the LLM (with or without RAG).
        *   `stream_chat(self, query: str)`: Streams a chat response from the LLM.

### File: `C:\AI\pyramid-rag\backend\app\services\search_service.py`

*   **Class: `SearchService`**
    *   **Description:** A service for performing semantic search using the vector store.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\services\search_service.py`
    *   **Methods:**
        *   `__init__(self, vector_store: VectorStore)`: Initializes the service with a vector store.
        *   `search(self, query: str, top_k: int = 5) -> List[dict]`: Performs a search and returns the top k results.

### File: `C:\AI\pyramid-rag\backend\app\utils\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `utils` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\utils\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\utils\startup.py`

*   **Functions:**
    *   `create_initial_superuser()`:
        *   **Description:** A function to create an initial superuser in the database if one doesn't exist. This is likely called on application startup.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\utils\startup.py`

### File: `C:\AI\pyramid-rag\backend\app\vector_store.py`

*   **Class: `VectorStore`**
    *   **Description:** A class for managing the vector store. It uses a PostgreSQL database with the `pgvector` extension to store and query document embeddings.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\vector_store.py`
    *   **Methods:**
        *   `__init__(self, db_session: Session)`: Initializes the vector store with a database session.
        *   `add_documents(self, documents: List[schemas.DocumentChunk])`: Adds document chunks and their embeddings to the vector store.
        *   `search(self, query_embedding: List[float], top_k: int = 5) -> List[dict]`: Searches the vector store for the most similar document chunks.

### File: `C:\AI\pyramid-rag\backend\app\workers\__init__.py`

*   **Description:** This is an empty `__init__.py` file. It signifies that the `workers` directory is a Python package.
*   **Location:** `C:\AI\pyramid-rag\backend\app\workers\__init__.py`

### File: `C:\AI\pyramid-rag\backend\app\workers\celery_app.py`

*   **Celery App:**
    *   **Description:** This file configures and creates the Celery application instance. It sets up the broker (Redis) and result backend.
    *   **Location:** `C:\AI\pyramid-rag\backend\app\workers\celery_app.py`

### File: `C:\AI\pyramid-rag\backend\app\workers\document_tasks.py`

*   **Celery Tasks:**
    *   `process_document_task(document_id: int)`:
        *   **Description:** A Celery task that processes an uploaded document. It reads the document, splits it into chunks, and saves the chunks to the database. It then triggers the embedding task for the new chunks.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\workers\document_tasks.py`

### File: `C:\AI\pyramid-rag\backend\app\workers\embedding_tasks.py`

*   **Celery Tasks:**
    *   `create_embeddings_for_chunks_task(chunk_ids: List[int])`:
        *   **Description:** A Celery task that creates embeddings for a list of document chunks. It uses the `EmbeddingService` to generate the embeddings and saves them to the vector store.
        *   **Location:** `C:\AI\pyramid-rag\backend\app\workers\embedding_tasks.py`

### File: `C:\AI\pyramid-rag\backend\create_admin.py`

*   **Script:**
    *   **Description:** A script to create an admin user in the database. It prompts for a username and password.
    *   **Location:** `C:\AI\pyramid-rag\backend\create_admin.py`

### File: `C:\AI\pyramid-rag\backend\list_users.py`

*   **Script:**
    *   **Description:** A script to list all users in the database.
    *   **Location:** `C:\AI\pyramid-rag\backend\list_users.py`

### File: `C:\AI\pyramid-rag\backend\reset_admin_password.py`

*   **Script:**
    *   **Description:** A script to reset the password of an admin user.
    *   **Location:** `C:\AI\pyramid-rag\backend\reset_admin_password.py`

### File: `C:\AI\pyramid-rag\backend\reset_db.py`

*   **Script:**
    *   **Description:** A script to reset the database by dropping and recreating all tables.
    *   **Location:** `C:\AI\pyramid-rag\backend\reset_db.py`

### File: `C:\AI\pyramid-rag\backend\start_waitress.py`

*   **Script:**
    *   **Description:** A script to start the FastAPI application using the Waitress production server.
    *   **Location:** `C:\AI\pyramid-rag\backend\start_waitress.py`

### File: `C:\AI\pyramid-rag\backend\test_minimal.py`

*   **Test Script:**
    *   **Description:** A script to test the minimal FastAPI application (`main_minimal.py`).
    *   **Location:** `C:\AI\pyramid-rag\backend\test_minimal.py`

### File: `C:\AI\pyramid-rag\backend\update_admin_password.py`

*   **Script:**
    *   **Description:** A script to update the password of an admin user.
    *   **Location:** `C:\AI\pyramid-rag\backend\update_admin_password.py`

## Frontend

### File: `C:\AI\pyramid-rag\frontend\src\pages\ChatInterface.tsx`

*   **Component: `ChatInterface`**
    *   **Description:** The main chat interface component. It includes a message display area, a text input for sending messages, and options for controlling the chat behavior (e.g., toggling RAG). It manages the state of the chat conversation, including the list of messages and the current input.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\ChatInterface.tsx`
    *   **State:**
        *   `messages`: An array of chat messages in the conversation.
        *   `input`: The current text in the message input field.
        *   `isStreaming`: A boolean indicating if a response is currently being streamed.
    *   **Functions:**
        *   `handleSend()`: Sends the current message to the backend and updates the chat with the response.
        *   `handleInputChange()`: Updates the `input` state as the user types.

### File: `C:\AI\pyramid-rag\frontend\src\services\MCPClient.ts`

*   **Class: `MCPClient`**
    *   **Description:** A client for interacting with the MCP (Model-Controller-Processor) network server. It provides a method to send tool calls to the backend.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\services\MCPClient.ts`
    *   **Methods:**
        *   `constructor(host: string, port: number)`: Initializes the client with the server's host and port.
        *   `sendToolCall(toolName: string, args: any): Promise<any>`: Sends a tool call to the server and returns the result.

### File: `C:\AI\pyramid-rag\frontend\src\utils\chatDocuments.test.ts`

*   **Test File:**
    *   **Description:** This file contains unit tests for the `chatDocuments` utility functions.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\utils\chatDocuments.test.ts`

### File: `C:\AI\pyramid-rag\frontend\src\utils\chatDocuments.ts`

*   **Utility Functions:**
    *   `addDocumentToChat(document: Document): void`:
        *   **Description:** A function to add a document to the current chat context.
        *   **Location:** `C:\AI\pyramid-rag\frontend\src\utils\chatDocuments.ts`
    *   `removeDocumentFromChat(documentId: string): void`:
        *   **Description:** A function to remove a document from the chat context.
        *   **Location:** `C:\AI\pyramid-rag\frontend\src\utils\chatDocuments.ts`

### File: `C:\AI\pyramid-rag\frontend\src\pages\ChatInterface.legacy.tsx`

*   **Component: `ChatInterfaceLegacy`**
    *   **Description:** A previous or alternative version of the chat interface. It might contain older logic or a different UI structure.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\ChatInterface.legacy.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\App.tsx`

*   **Component: `App`**
    *   **Description:** The main application component. It sets up the application's routing, theme, and authentication context. It defines the overall layout and structure of the application, including the main routes for pages like Login, Dashboard, and Chat.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\App.tsx`
    *   **Routing:** Uses `react-router-dom` to define the application's routes.
    *   **Contexts:** Wraps the application in `AuthProvider` and `ThemeProvider` to provide global state for authentication and theming.

### File: `C:\AI\pyramid-rag\frontend\src\AppFixed.tsx`

*   **Component: `AppFixed`**
    *   **Description:** A fixed or alternative version of the main `App` component. It might contain bug fixes or different implementations of the application's core structure.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\AppFixed.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\AppSimple.tsx`

*   **Component: `AppSimple`**
    *   **Description:** A simplified version of the main `App` component, likely for testing or demonstration purposes. It might have a minimal UI and a reduced set of features.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\AppSimple.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\components\Layout.tsx`

*   **Component: `Layout`**
    *   **Description:** A layout component that provides a consistent structure for the application's pages. It typically includes a header, a sidebar for navigation, and a main content area.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\components\Layout.tsx`
    *   **Props:**
        *   `children`: The content to be rendered within the main content area of the layout.

### File: `C:\AI\pyramid-rag\frontend\src\components\LoadingSpinner.tsx`

*   **Component: `LoadingSpinner`**
    *   **Description:** A simple component that displays a loading spinner, typically used to indicate that data is being fetched or a process is running.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\components\LoadingSpinner.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\components\ProtectedRoute.tsx`

*   **Component: `ProtectedRoute`**
    *   **Description:** A component that protects routes from unauthenticated access. It checks if the user is authenticated and, if not, redirects them to the login page.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\components\ProtectedRoute.tsx`
    *   **Props:**
        *   `children`: The component to render if the user is authenticated.

### File: `C:\AI\pyramid-rag\frontend\src\components\SimpleUpload.tsx`

*   **Component: `SimpleUpload`**
    *   **Description:** A basic file upload component. It provides a button or a drag-and-drop area for users to select a file and upload it to the server.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\components\SimpleUpload.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\contexts\AuthContext.tsx`

*   **Context: `AuthContext`**
    *   **Description:** A React context for managing authentication state throughout the application. It provides the current user, a login function, a logout function, and the authentication token.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\contexts\AuthContext.tsx`
    *   **Provider: `AuthProvider`**
        *   **Description:** The provider component for the `AuthContext`. It manages the authentication state and makes it available to all child components.

### File: `C:\AI\pyramid-rag\frontend\src\contexts\ThemeContext.tsx`

*   **Context: `ThemeContext`**
    *   **Description:** A React context for managing the application's theme. It allows users to switch between light and dark modes.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\contexts\ThemeContext.tsx`
    *   **Provider: `ThemeProvider`**
        *   **Description:** The provider component for the `ThemeContext`. It manages the current theme and makes it available to all child components.

### File: `C:\AI\pyramid-rag\frontend\src\i18n.ts`

*   **Internationalization (i18n) Setup:**
    *   **Description:** This file configures the `i18next` library for internationalization. It sets up the supported languages, loads the translation files, and initializes the library.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\i18n.ts`

### File: `C:\AI\pyramid-rag\frontend\src\index.tsx`

*   **Description:** This is the main entry point for the React application. It renders the root `App` component into the DOM.
*   **Location:** `C:\AI\pyramid-rag\frontend\src\index.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\main.tsx`

*   **Description:** This is the main entry point for the React application, used with Vite. It renders the root `App` component into the DOM.
*   **Location:** `C:\AI\pyramid-rag\frontend\src\main.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Admin.tsx`

*   **Component: `Admin`**
    *   **Description:** The admin dashboard page. It provides administrative functions, such as viewing server status, managing users, and monitoring Celery workers.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Admin.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Dashboard.tsx`

*   **Component: `Dashboard`**
    *   **Description:** The main dashboard page that users see after logging in. It might display an overview of their documents, recent chats, or other relevant information.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Dashboard.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Documents.tsx`

*   **Component: `Documents`**
    *   **Description:** A page for viewing and managing uploaded documents. It typically displays a list of documents and allows users to view, delete, or search them.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Documents.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\DocumentUpload.tsx`

*   **Component: `DocumentUpload`**
    *   **Description:** A page dedicated to uploading new documents. It might provide a more advanced upload interface than the `SimpleUpload` component, with features like drag-and-drop and progress indicators.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\DocumentUpload.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Login.tsx`

*   **Component: `Login`**
    *   **Description:** The login page for the application. It provides a form for users to enter their credentials and authenticate.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Login.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\LoginSimple.tsx`

*   **Component: `LoginSimple`**
    *   **Description:** A simplified version of the login page, possibly for testing or as a fallback.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\LoginSimple.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Profile.tsx`

*   **Component: `Profile`**
    *   **Description:** The user profile page. It allows users to view and edit their personal information.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Profile.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\pages\Search.tsx`

*   **Component: `Search`**
    *   **Description:** A page for performing semantic search across all documents. It includes a search bar and a results display area.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\pages\Search.tsx`

### File: `C:\AI\pyramid-rag\frontend\src\store\index.ts`

*   **Redux Store Setup:**
    *   **Description:** This file configures the Redux Toolkit store for state management. It defines the root reducer and any middleware.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\store\index.ts`

### File: `C:\AI\pyramid-rag\frontend\src\theme.ts`

*   **Material-UI Theme:**
    *   **Description:** This file defines the custom Material-UI theme for the application. It includes color palettes, typography, and other styling options for both light and dark modes.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\theme.ts`

### File: `C:\AI\pyramid-rag\frontend\src\vite-env.d.ts`

*   **Vite Environment Types:**
    *   **Description:** This file contains TypeScript type definitions for Vite's environment variables.
    *   **Location:** `C:\AI\pyramid-rag\frontend\src\vite-env.d.ts`

## Other Project Files

### Project Root Files

*   **File: `C:\AI\.gitignore`**
    *   **Description:** This file specifies which files and directories should be ignored by Git. It includes common Python and Node.js artifacts, as well as environment files.
    *   **Location:** `C:\AI\.gitignore`

*   **File: `C:\AI\AGENTS.md`**
    *   **Description:** This markdown file provides guidelines for AI agents working on the repository. It covers project structure, build and test commands, coding style, commit guidelines, and security tips.
    *   **Location:** `C:\AI\AGENTS.md`

*   **File: `C:\AI\Anforderungen.txt`**
    *   **Description:** A German text file outlining the requirements for the Pyramid RAG Platform. It covers user roles, functional scope (chat, documents, temp chats), non-functional requirements, technical architecture, security, data model, and a sketch of the API.
    *   **Location:** `C:\AI\Anforderungen.txt`

*   **File: `C:\AI\CHAT_INTERFACE_UPGRADE_NOTES.md`**
    *   **Description:** Notes on upgrading the chat interface. It details backend and frontend objectives to enhance the chat experience by integrating uploaded documents for prompts and previews.
    *   **Location:** `C:\AI\CHAT_INTERFACE_UPGRADE_NOTES.md`

*   **File: `C:\AI\README.md`**
    *   **Description:** A brief README file that seems to be a part of a larger one, specifying software prerequisites for the project.
    *   **Location:** `C:\AI\README.md`

### `pyramid-rag` Directory Files

*   **File: `C:\AI\pyramid-rag\CLAUDE.md`**
    *   **Description:** A detailed documentation file for the Claude AI agent. It includes a critical status update, a project overview, a code review checklist, known issues, required actions, architecture details, and implementation status of various features. It seems to be a central document for the AI to track its progress and context.
    *   **Location:** `C:\AI\pyramid-rag\CLAUDE.md`

*   **File: `C:\AI\pyramid-rag\CODE_REVIEW_RESULTS.md`**
    *   **Description:** This file documents the results of a code review. It highlights critical issues, import path inconsistencies, and password hash storage problems. It also provides a checklist of fixes and validation steps.
    *   **Location:** `C:\AI\pyramid-rag\CODE_REVIEW_RESULTS.md`

*   **File: `C:\AI\pyramid-rag\CODEBASE_REVIEW.md`**
    *   **Description:** A comprehensive review of the codebase, focusing on variable naming and consistency. It maps out critical variables for user authentication, database connections, model field names, and API endpoints.
    *   **Location:** `C:\AI\pyramid-rag\CODEBASE_REVIEW.md`

*   **File: `C:\AI\pyramid-rag\debug_422.py`**
    *   **Description:** A Python script for debugging HTTP 422 Unprocessable Entity errors. It sends various test cases to the chat endpoint to identify the cause of the error.
    *   **Location:** `C:\AI\pyramid-rag\debug_422.py`

*   **File: `C:\AI\pyramid-rag\docker-compose-minimal.yml`**
    *   **Description:** A minimal Docker Compose file for a development environment. It includes services for the database, Redis, a minimal backend, the MCP server, Ollama, and a simple frontend.
    *   **Location:** `C:\AI\pyramid-rag\docker-compose-minimal.yml`

*   **File: `C:\AI\pyramid-rag\docker-compose.yml`**
    *   **Description:** The main Docker Compose file for the full application. It orchestrates all the services, including the backend, frontend, database, Redis, Celery workers, Ollama, Nginx, Prometheus, and Grafana.
    *   **Location:** `C:\AI\pyramid-rag\docker-compose.yml`

*   **File: `C:\AI\pyramid-rag\DOCUMENT_UPLOAD_UPDATE.md`**
    *   **Description:** This document outlines the updates made to the document upload system, including the replacement of the "Indexieren" toggle with a "In Datenbank speichern" toggle for better clarity.
    *   **Location:** `C:\AI\pyramid-rag\DOCUMENT_UPLOAD_UPDATE.md`

*   **File: `C:\AI\pyramid-rag\fix_admin_password.py`**
    *   **Description:** A Python script to generate a correct bcrypt hash for the admin password and print the SQL command to update it in the database.
    *   **Location:** `C:\AI\pyramid-rag\fix_admin_password.py`

*   **File: `C:\AI\pyramid-rag\fix_and_restart.bat`**
    *   **Description:** A Windows batch script to stop, clean, and restart the Docker containers for the application.
    *   **Location:** `C:\AI\pyramid-rag\fix_and_restart.bat`

*   **File: `C:\AI\pyramid-rag\fix_database.py`**
    *   **Description:** A Python script to fix the database schema by adding missing columns and tables.
    *   **Location:** `C:\AI\pyramid-rag\fix_database.py`

*   **File: `C:\AI\pyramid-rag\IMPORT_FIX_RESULTS.md`**
    *   **Description:** This file documents the results of fixing import paths in the codebase, moving from a centralized config to environment variables.
    *   **Location:** `C:\AI\pyramid-rag\IMPORT_FIX_RESULTS.md`

*   **File: `C:\AI\pyramid-rag\MCP_MIGRATION_PLAN.md`**
    *   **Description:** A plan for migrating all LLM-related functions from the REST API to the Model Context Protocol (MCP) for better standardization and integration with Microsoft Dynamics.
    *   **Location:** `C:\AI\pyramid-rag\MCP_MIGRATION_PLAN.md`

*   **File: `C:\AI\pyramid-rag\RAG_IMPLEMENTATION_GUIDE.md`**
    *   **Description:** A guide for implementing the RAG pipeline, including architecture, database schema updates, implementation phases, and technology stack.
    *   **Location:** `C:\AI\pyramid-rag\RAG_IMPLEMENTATION_GUIDE.md`

*   **File: `C:\AI\pyramid-rag\README.md`**
    *   **Description:** The main README file for the project. It provides an overview, system requirements, quick start guide, architecture diagram, project structure, and information on configuration, monitoring, security, and maintenance.
    *   **Location:** `C:\AI\pyramid-rag\README.md`

*   **File: `C:\AI\pyramid-rag\restart_all.bat`**
    *   **Description:** A Windows batch script to restart all Docker containers for the application.
    *   **Location:** `C:\AI\pyramid-rag\restart_all.bat`

*   **File: `C:\AI\pyramid-rag\RUN_ALL_TESTS.py`**
    *   **Description:** A comprehensive Python test suite for the Pyramid RAG platform. It tests all major features, including health checks, authentication, document management, chat, and admin features.
    *   **Location:** `C:\AI\pyramid-rag\RUN_ALL_TESTS.py`

*   **File: `C:\AI\pyramid-rag\setup.bat`**
    *   **Description:** A Windows batch script for setting up the project. It checks for dependencies, creates configuration files, and starts all the services.
    *   **Location:** `C:\AI\pyramid-rag\setup.bat`

*   **File: `C:\AI\pyramid-rag\setup.sh`**
    *   **Description:** A shell script for setting up the project on Linux or macOS. It performs similar actions to the `setup.bat` script.
    *   **Location:** `C:\AI\pyramid-rag\setup.sh`

*   **File: `C:\AI\pyramid-rag\STATUS.md`**
    *   **Description:** A status report for the Pyramid RAG Platform, indicating that the system is operational with UI improvements. It details recent changes, service status, and known issues.
    *   **Location:** `C:\AI\pyramid-rag\STATUS.md`

*   **File: `C:\AI\pyramid-rag\SYSTEM_DOCUMENTATION.md`**
    *   **Description:** The main system documentation, providing an overview of the system, RAG pipeline status, architecture, and usage instructions.
    *   **Location:** `C:\AI\pyramid-rag\SYSTEM_DOCUMENTATION.md`

*   **File: `C:\AI\pyramid-rag\SYSTEM_STATUS_REPORT.md`**
    *   **Description:** A detailed system status report, documenting fixed issues, current system health, and recommended next steps.
    *   **Location:** `C:\AI\pyramid-rag\SYSTEM_STATUS_REPORT.md`

*   **File: `C:\AI\pyramid-rag\UI_CHANGES_COMPLETED.md`**
    *   **Description:** This file documents the completion of UI changes requested by the user, including the removal and relocation of toggles in the chat interface.
    *   **Location:** `C:\AI\pyramid-rag\UI_CHANGES_COMPLETED.md`

*   **File: `C:\AI\pyramid-rag\upload_sample_docs.py`**
    *   **Description:** A Python script to upload sample documents to the RAG system. It logs in, uploads a predefined list of documents, and verifies that they are searchable.
    *   **Location:** `C:\AI\pyramid-rag\upload_sample_docs.py`

### `docker` Directory

*   **File: `C:\AI\pyramid-rag\docker\nginx\nginx.conf`**
    *   **Description:** The configuration file for the Nginx reverse proxy. It defines how traffic is routed to the frontend and backend services.
    *   **Location:** `C:\AI\pyramid-rag\docker\nginx\nginx.conf`

*   **File: `C:\AI\pyramid-rag\docker\postgres\init.sql`**
    *   **Description:** An SQL script that is run when the PostgreSQL container is first created. It likely sets up the initial database, users, and roles.
    *   **Location:** `C:\AI\pyramid-rag\docker\postgres\init.sql`

*   **File: `C:\AI\pyramid-rag\docker\prometheus\prometheus.yml`**
    *   **Description:** The configuration file for the Prometheus monitoring service. It defines which services to scrape for metrics.
    *   **Location:** `C:\AI\pyramid-rag\docker\prometheus\prometheus.yml`

### `docs` Directory

*   **File: `C:\AI\pyramid-rag\docs\local_python_setup.md`**
    *   **Description:** A markdown file with instructions on how to set up a local Python development environment for the project.
    *   **Location:** `C:\AI\pyramid-rag\docs\local_python_setup.md`

*   **File: `C:\AI\pyramid-rag\docs\upload_pipeline_log_2025-10-06.md`**
    *   **Description:** A log file from October 6, 2025, detailing the upload pipeline's activities.
    *   **Location:** `C:\AI\pyramid-rag\docs\upload_pipeline_log_2025-10-06.md`

*   **File: `C:\AI\pyramid-rag\docs\upload_pipeline_log_2025-10-07.md`**
    *   **Description:** A log file from October 7, 2025, detailing the upload pipeline's activities.
    *   **Location:** `C:\AI\pyramid-rag\docs\upload_pipeline_log_2025-10-07.md`

### `sample_docs` Directory

*   **File: `C:\AI\pyramid-rag\sample_docs\pipeline_test.pdf`**
    *   **Description:** A PDF file used for testing the document processing pipeline.
    *   **Location:** `C:\AI\pyramid-rag\sample_docs\pipeline_test.pdf`

*   **File: `C:\AI\pyramid-rag\sample_docs\product_catalog.txt`**
    *   **Description:** A text file containing a product catalog, used as sample data for the RAG system.
    *   **Location:** `C:\AI\pyramid-rag\sample_docs\product_catalog.txt`

*   **File: `C:\AI\pyramid-rag\sample_docs\security_policy.txt`**
    *   **Description:** A text file containing a security policy, used as sample data.
    *   **Location:** `C:\AI\pyramid-rag\sample_docs\security_policy.txt`

*   **File: `C:\AI\pyramid-rag\sample_docs\support_guide.txt`**
    *   **Description:** A text file containing a support guide, used as sample data.
    *   **Location:** `C:\AI\pyramid-rag\sample_docs\support_guide.txt`
