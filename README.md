<h1 align="center" id="title">Ria Scraper</h1>

<p id="description">This project is an asynchronous scraper built with FastAPI designed to collect used car listings from the AutoRia platform. It crawls multiple pages of listings extracts detailed information for each car including price odometer reading seller details phone numbers (via API) images VIN and more. The collected data is stored in a PostgreSQL database to facilitate further analysis or integration.</p>

  
  
<h2>✨ Features</h2>

Here're some of the project's best features:

*   Asynchronous scraping for high performance using aiohttp and asyncio.
*   Robust data extraction with parsing of complex page elements and JSON-LD metadata.
*   Dockerized setup with docker-compose for easy deployment including PostgreSQL.
*   REST API endpoints with FastAPI providing:
    - Listing of cars with pagination (limit and offset).
    - Retrieval of individual car details by ID.
    - Trigger scraping and database dump tasks asynchronously.
*   Scheduled scraping: scraper runs automatically at configured daily intervals using a task scheduler (APScheduler).
*   Duplication prevention in database using upsert on car URL.
*   Automatic daily database dumps with storage in a configurable directory.

<h2>🛠️ Installation Steps:</h2>

<p>1. Clone the repository</p>

```
git clone https://github.com/DmitriyMushtruk/ria_scraper_api.git
```

<p>2. Create and configure .env file. Copy the example environment variables file and edit the values as needed</p>

```
cp .env.example .env
```

<p>3. Build and start services with Docker Compose</p>

```
docker-compose up --build
```

<p>4. Access the API</p>

```
The FastAPI server will be available at http://localhost:8000. Interactive API docs are at http://localhost:8000/docs.
```

<p>5. Stopping the application</p>

```
docker-compose down
```

<h3>Notes</h3>

*   Database data and dumps are stored in Docker volumes and local dumps/ directory, so data persists across container restarts.
*   Scheduled scraping and database dump tasks run inside the FastAPI container automatically according to configured times.
*   Modify .env to tune scraper behavior and daily schedules.


<h3>Makefile Commands</h3>
This project includes a convenient Makefile to simplify common Docker Compose operations. You can use these commands to build, run, stop, and access the application containers.

<p>Available commands:</p>

*   ```make build``` - Build Docker images for all services.
*   ```make up``` - Build (if needed) and start all containers in the foreground.
*   ```make down``` - Stop and remove containers, networks, volumes, and images created by ```docker-compose```.
*   ```make bash``` - Open an interactive bash shell inside the running app container (```app``` service).

<p>Usage example:</p>

```
make build    # Build images
make up       # Start services
make bash     # Access app container shell
make down     # Stop and clean up everything
```


Scraper Overview
<h2>📝 Scraper Overview</h2>
The RiaScraper class implements an asynchronous scraper designed to collect car data from the AutoRia website. It uses a classic producer-consumer pattern with load balancing and concurrency control.

<p>Usage example:</p>


<h3>Key Components and Responsibilities</h3>

* Initialization:
    - Creates required objects in the constructor and __aenter__ context manager:
        - Asynchronous HTTP session (aiohttp.ClientSession).
        - Page fetching utility (PageFetcher).
        - Link extraction helper (LinkFetcher) and car page parser (CarDataFetcher).
        - Database manager (DBManager).
        - Semaphore for limiting concurrent requests.
        - Asynchronous queue (asyncio.Queue) to store car listing URLs.


<h3>How It Works</h3>

* start()
    - Launches the main scraping logic by creating:
        - a producer task,
        - multiple worker tasks (based on max_workers).
    - Waits for the producer to finish and for the queue to be processed.
    - Gracefully cancels all worker tasks afterward.
* _producer()
    - Iterates over listing pages starting from the default page.
    - Downloads each listing page HTML using ```page_fetcher.get```.
    - Extracts car links via ```link_fetcher.extract_links```.
    - Tracks consecutive empty pages; stops if it reaches a configured threshold (```max_empty_pages```).
    - Enqueues discovered car URLs into the queue for workers to process.
* _worker(index)
    - Continuously consumes URLs from the queue.
    - Downloads and parses each car page HTML with ```car_fetcher.parse_car_page```.
    - Persists parsed data to the database through ```db_manager.write_car```.
    - Controls request concurrency using the semaphore to avoid overloading the server.
    - Catches and logs exceptions; marks each task as done after processing.


<h3>Implementation Highlights</h3>

* Asynchronous design: Utilizes ```asyncio```, ```aiohttp```, and async context managers for efficient IO operations.

* Concurrency control: Employs ```asyncio.Semaphore``` to limit simultaneous outbound HTTP requests, preventing bans and overload.

* Task queue: Manages car URLs with ```asyncio.Queue```, enabling coordinated task distribution among multiple workers.

* Robust error handling: Logs errors during page fetch, allowing scraping to continue uninterrupted.

* Context manager support: Properly opens and closes resources ensuring clean startup and shutdown.
