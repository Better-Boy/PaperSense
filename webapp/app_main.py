"""FastAPI application for ArXiv paper search and chat functionality.

This module provides a web API for searching ArXiv papers and chatting with 
AI agents about specific papers using MindsDB integration.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import arxiv_pipeline, psql, utils, config_loader as config
from src.mindsdb import agent, knowledge_base, mdb_server
from src.models import ChatRequest, ChatResponse, SearchResponse, ErrorResponse
from src.models.common import HealthStatus
from src.models.search import PaperResult

os.makedirs('logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=config.app.LOG_LEVEL,
    format=config.app.LOG_FORMAT,
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global instances
_mdb: Optional[mdb_server.MDBServer] = None
_kb: Optional[knowledge_base.KnowledgeBase] = None
_psql: Optional[psql.PostgresHandler] = None
_agent: Optional[agent.Agent] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle for startup and shutdown operations."""
    global _mdb, _kb, _psql, _agent
    
    try:
        # Startup
        logger.info("Starting application initialization...")
        
        _mdb = mdb_server.MDBServer()
        _psql = psql.PostgresHandler()
        _kb = knowledge_base.KnowledgeBase(_mdb)
        _agent = agent.Agent(_mdb)
        
        # Run warmup
        try:
            
            from .warmup import WarmUp
            warmup = WarmUp(_mdb, _kb, _psql)
            warmup.start()
            logger.info("Warmup completed successfully")
        except ImportError as e:
            logger.warning(f"Warmup module not found: {e}")
        except Exception as e:
            logger.error(f"Warmup failed: {e}")
            raise
        
        logger.info("Application startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Starting application shutdown...")
        
        if _psql:
            try:
                _psql.disconnect()
                logger.info("PostgreSQL connection closed")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection: {e}")
        
        if _mdb:
            try:
                _mdb.disconnect()
                logger.info("MindsDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MindsDB connection: {e}")
        
        logger.info("Application shutdown completed")


# Initialize FastAPI app
app = FastAPI(
    title="ArXiv Paper Search and Chat API",
    description="API for searching ArXiv papers and chatting with AI agents about them",
    version="1.0.0",
    lifespan=lifespan
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Set up templates
templates = Jinja2Templates(directory=TEMPLATE_DIR)


def _validate_search_filters(category: Optional[str], year: Optional[str]) -> Dict[str, str]:
    """Validate and format search filters.
    
    Args:
        category: Paper category filter
        year: Publication year filter
        
    Returns:
        Dictionary of validated filters
        
    Raises:
        HTTPException: If validation fails
    """
    filters = {}
    
    if category:
        category = category.strip()
        if category not in ["cs", "physics", "economics", "math", "eecs"]:
            raise HTTPException(
                status_code=400,
                detail="Unknown category. Allowed categories - cs, physics, economics, math, eecs"
            )
        filters["category"] = category
    
    if year:
        year = year.strip()
        try:
            year_int = int(year)
            if year_int < 1991 or year_int > 2030:  # ArXiv started in 1991
                raise ValueError("Year out of valid range")
            filters["year"] = year
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid year format. Must be a valid year between 1991-2030"
            )
    
    return filters


def _convert_to_paper_results(raw_results: list) -> list[PaperResult]:
    """Convert raw search results to PaperResult models.
    
    Args:
        raw_results: Raw results from knowledge base search
        
    Returns:
        List of PaperResult models
    """
    paper_results = []
    
    for result in raw_results:
        try:
            # Handle different possible result formats
            if isinstance(result, dict):
                paper_result = PaperResult(
                    article_id=result.get('article_id', result.get('id', '')),
                    title=result.get('title', ''),
                    authors=result.get('authors', ''),
                    summary=result.get('summary', ''),
                    categories=result.get('categories', []),
                    published_year=result.get('published_year', ''),
                    relevance=result.get('relevance', '')
                )
                paper_results.append(paper_result)
            else:
                logger.warning(f"Unexpected result format: {type(result)}")
        except Exception as e:
            logger.error(f"Error converting result to PaperResult: {e}")
            continue
    
    return paper_results


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request) -> HTMLResponse:
    """Serve the main index page.
    
    Args:
        request: FastAPI request object
        
    Returns:
        HTML response with the index template
    """
    try:
        logger.info("Serving index page")
        return templates.TemplateResponse("index.html", {"request": request})
    except Exception as e:
        logger.error(f"Error serving index page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/search", response_model=SearchResponse)
async def search_papers(
    query: str = Query(..., min_length=1, max_length=200, description="Search query"),
    category: Optional[str] = Query(None, description="Paper category filter"),
    year: Optional[str] = Query(None, description="Publication year filter")
) -> SearchResponse:
    """Search for ArXiv papers based on query and optional filters.
    
    Args:
        query: Search query string
        category: Optional category filter
        year: Optional year filter
        
    Returns:
        SearchResponse with search results
        
    Raises:
        HTTPException: If search fails or validation fails
    """
    if not _kb:
        raise HTTPException(status_code=503, detail="Knowledge base not initialized")
    
    try:
        # Validate and clean inputs
        query = query.strip()
        filters = _validate_search_filters(category, year)
        
        logger.info(f"Searching papers with query: '{query}', filters: {filters}")
        
        # Perform search
        raw_results = _kb.search(query, filters)
        
        # Convert to PaperResult models
        paper_results = _convert_to_paper_results(raw_results if raw_results else [])
        
        response = SearchResponse(
            results=paper_results
        )
        
        logger.info(f"Search completed. Found {len(paper_results)} results")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed for query '{query}': {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search operation failed: {str(e)}"
        )


@app.get("/api/chat-ui", response_class=HTMLResponse)
async def get_chat_ui(
    request: Request,
    query: str = Query(..., min_length=1, description="ArXiv paper ID")
) -> HTMLResponse:
    """Get chat UI for a specific ArXiv paper.
    
    Args:
        request: FastAPI request object
        query: ArXiv paper ID
        
    Returns:
        HTML response with chat interface
        
    Raises:
        HTTPException: If paper processing fails
    """
    if not all([_kb, _psql, _agent]):
        raise HTTPException(status_code=503, detail="Services not initialized")
    
    try:
        # Validate ArXiv ID format using ChatRequest model
        try:
            # Use the model for validation
            temp_request = ChatRequest(arxiv_id=query, query="temp")
            arxiv_id = temp_request.arxiv_id
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid ArXiv ID format: {str(e)}"
            )
        
        logger.info(f"Setting up chat UI for paper: {arxiv_id}")
        
        # Generate names and URLs
        arxiv_paper_link = f"https://arxiv.org/pdf/{arxiv_id}"
        paper_agent_name = utils.generate_agent_name(arxiv_id)
        paper_kb_name = utils.generate_kb_name(arxiv_id)
        
        # Check if agent already exists
        if not _agent.agent_exists(paper_agent_name):
            logger.info(f"Creating new agent for paper: {arxiv_id}")
            
            try:
                # Process paper through pipeline
                arxiv_pipe = arxiv_pipeline.ArxivProcessPipeline(arxiv_id, _kb, _psql)
                arxiv_pipe.start()
                
                # Create agent
                _agent.create(paper_agent_name, [paper_kb_name], [])
                logger.info(f"Agent created successfully: {paper_agent_name}")
                
            except Exception as e:
                logger.error(f"Failed to process paper {arxiv_id}: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process paper: {str(e)}"
                )
        else:
            logger.info(f"Using existing agent: {paper_agent_name}")
        
        return templates.TemplateResponse(
            "chat.html",
            {
                "request": request,
                "arxiv_link": arxiv_paper_link
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up chat UI for {query}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup chat interface: {str(e)}"
        )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_paper(request: Request) -> ChatResponse:
    """Chat with an AI agent about a specific ArXiv paper.
    
    Args:
        request: FastAPI request object containing chat request data
        
    Returns:
        ChatResponse with agent's reply
        
    Raises:
        HTTPException: If chat operation fails
    """
    if not _agent:
        raise HTTPException(status_code=503, detail="Agent service not initialized")
    
    try:
        # Parse and validate request body
        try:
            body = await request.json()
            chat_request = ChatRequest(**body)
        except Exception as e:
            logger.error(f"Invalid request format: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid request format: {str(e)}"
            )
        
        logger.info(f"Processing chat query for paper {chat_request.arxiv_id}")
        
        # Generate agent name
        paper_agent_name = utils.generate_agent_name(chat_request.arxiv_id)
        
        # Check if agent exists
        existing_agents = _agent.ls()
        if paper_agent_name not in existing_agents:
            logger.error(f"Agent not found: {paper_agent_name}")
            raise HTTPException(
                status_code=404,
                detail=f"Agent for paper {chat_request.arxiv_id} not found. "
                       "Please visit the chat UI first to initialize the agent."
            )
        
        # Perform chat
        try:
            response_text = _agent.chat(paper_agent_name, chat_request.query)
            
            response = ChatResponse(response=response_text)
            
            logger.info(f"Chat completed successfully for paper {chat_request.arxiv_id}")
            return response
            
        except Exception as e:
            logger.error(f"Chat operation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Chat operation failed: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )


@app.get("/status", response_model=HealthStatus)
async def get_status() -> HealthStatus:
    """Get application health status.
    
    Returns:
        HealthStatus with status information
    """
    try:
        services = {
            "mindsdb": _mdb is not None,
            "knowledge_base": _kb is not None,
            "postgres": _psql is not None,
            "agent": _agent is not None
        }
        
        # Check if all services are initialized
        all_ready = all(services.values())
        status = "ready" if all_ready else "partial"
        
        health_status = HealthStatus(
            status=status,
            services=services
        )
        
        logger.debug(f"Status check: {health_status.dict()}")
        return health_status
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return HealthStatus(
            status="error",
            services={},
            error=str(e)
        )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle 404 errors with custom response."""
    error_response = ErrorResponse(
        error="Not Found",
        detail="The requested resource was not found",
        status_code=404
    )
    return JSONResponse(
        status_code=404,
        content=error_response.dict()
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle 500 errors with custom response."""
    logger.error(f"Internal server error on {request.url.path}: {exc.detail}")
    
    error_response = ErrorResponse(
        error="Internal Server Error",
        detail="An internal server error occurred",
        status_code=500
    )
    return JSONResponse(
        status_code=500,
        content=error_response.dict()
    )

