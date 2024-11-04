# Breach Browser

A fast and efficient full-text search engine for large text datasets with a clean web interface. Built with Python, Elasticsearch, and Flask.

![Preview](https://github.com/sooox-cc/breach-browser/blob/main/Screenshot_20241104_190348.png?raw=true)

## Features

- 🔍 Full-text search with advanced query syntax
- ⚡ Efficient chunking of large files
- 📊 Detailed search results with file metadata
- 🔧 Configurable results per page
- 💾 Progress tracking for large indexing operations
- 📝 Search highlighting with context
- 📈 Real-time search statistics

## Requirements

- Python 3.8+
- Elasticsearch 7.x
- Sufficient storage space for your dataset and indices

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

4. Install and start Elasticsearch:

On Arch Linux:
```bash
sudo pacman -S elasticsearch
sudo systemctl enable elasticsearch.service
sudo systemctl start elasticsearch.service
```

Using Docker:
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
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

## Performance Tips

1. Adjust the Elasticsearch heap size in `/etc/elasticsearch/jvm.options`:
```
-Xms1g
-Xmx1g
```

2. For very large datasets, consider increasing the chunk size and batch size

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
