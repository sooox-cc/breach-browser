# Breach Browser

A fast and efficient full-text search engine for large text datasets with a clean web interface. Built with Python, Elasticsearch, and Flask.

![Preview](https://github.com/sooox-cc/breach-browser/blob/main/preview.png?raw=true)

## Features

- 🔍 Full-text search with advanced query syntax
- ⚡ Efficient chunking of large files
- 📊 Detailed search results with file metadata
- 🔧 Progressive loading for faster search results
- 💾 Resume-capable indexing with progress tracking
- 📝 Search highlighting with context
- 📈 Real-time indexing statistics

## Requirements

- Python 3.8+
- Docker
- Sufficient storage space for your dataset and indices
- RAM, a whole lot of RAM

## Installation

1. Clone the repository:
```bash
git clone https://github.com/sooox-cc/breach-browser.git
cd breach-browser
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Setup Elasticsearch:

Create data Directory:
```bash
mkdir -p /opt/elasticsearch/data
chown -R 1000:1000 /opt/elasticsearch/data
```

Run Elasticsearch container:
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "ES_JAVA_OPTS=-Xms2g -Xmx2g" \
  -e "xpack.security.enabled=false" \
  -v /opt/elasticsearch/data:/usr/share/elasticsearch/data \
  --ulimit nofile=65535:65535 \
  --ulimit memlock=-1:-1 \
  elasticsearch:7.17.9
```

## Usage

1. Create a directory named `data` and place your text files there:
```bash
mkdir -p data
# Add your text files to data/
```

2. Run the application:
```bash
python app.py
```

3. Choose whether to reindex your data when prompted
4. Access the web interface at `http://localhost:5000`

## Search Syntax

The search interface supports various query types:
- `term1 AND term2` - Find documents containing both terms
- `"exact phrase"` - Find exact phrase matches
- `test*` - Find words starting with "test"
- `term~` - Find similar terms (fuzzy search)
- `term1 OR term2` - Find documents with either term
- `NOT term` - Exclude documents with this term

## Configuration

Edit in app.py:
- `chunk_size`: Text chunk size (default: 500KB)
- `batch_size`: Index batch size (default: 5)
- `port`: Web interface port (default: 5000)

## File Structure
```
breach-browser/
├── app.py             # Main application file
├── requirements.txt   # Python dependencies
├── static/            # Static assets
│   └── style.css      # CSS styles
├── templates/         # HTML templates
│   └── index.html     # Main search interface
└── data/              # Directory for text files (not included)
```

## Configuration

The application can be configured by modifying the following parameters in `app.py`:
- `chunk_size`: Size of text chunks (default: 500KB)
- `batch_size`: Number of documents per indexing batch (default: 5)
- `port`: Web interface port (default: 5000)
- `index_name`: Elasticsearch index name (default: text_documents)
- `data_dir`: The path of the data directory (default: `/data`)

## Security Considerations

This tool is intended for local use. When deploying:
1. Enable Elasticsearch security features
2. Configure proper authentication
3. Use HTTPS for the web interface
4. Restrict network access appropriately

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational and research purposes only. Users are responsible for ensuring they have appropriate permissions for any data they index and search.
