from flask import Flask, render_template, request, jsonify
from elasticsearch import Elasticsearch, helpers
import os
import hashlib
from tqdm import tqdm
import time
import sys

app = Flask(__name__)

class TextSearchEngine:
    def __init__(self, es_host='localhost', es_port=9200, index_name='text_documents'):
        self.es = Elasticsearch(
            [{'host': es_host, 'port': es_port}],
            http_compress=True,
            verify_certs=False
        )
        self.index_name = index_name
    
    def delete_index(self):
        """Delete the index if it exists"""
        if self.es.indices.exists(index=self.index_name):
            self.es.indices.delete(index=self.index_name)
            print(f"Deleted existing index: {self.index_name}")
        
    def create_index(self):
        """Create the Elasticsearch index with appropriate mappings"""
        settings = {
            "settings": {
                "number_of_shards": 5,
                "number_of_replicas": 1,
                "index.refresh_interval": "30s",
                "index.mapping.total_fields.limit": 10000,
                "index.max_result_window": 50000
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "filename": {"type": "keyword"},
                    "filepath": {"type": "keyword"},
                    "file_hash": {"type": "keyword"},
                    "chunk_number": {"type": "integer"},
                    "total_chunks": {"type": "integer"},
                    "file_size": {"type": "long"},
                    "indexed_date": {"type": "date"}
                }
            }
        }
        
        try:
            self.es.indices.create(index=self.index_name, body=settings)
            print(f"Created index: {self.index_name}")
        except Exception as e:
            print(f"Error creating index: {str(e)}")
            raise

    def chunk_text(self, text, chunk_size=500000):
        """Split text into chunks, preserving line integrity"""
        chunks = []
        lines = text.splitlines()
        current_chunk = []
        current_size = 0
        
        for line in lines:
            line_size = len(line.encode('utf-8'))
            if current_size + line_size > chunk_size and current_chunk:
                # Join current chunk and add to chunks
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_size = 0
            
            current_chunk.append(line)
            current_size += line_size
        
        # Add the last chunk if there is one
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks

    def format_size(self, size):
        """Convert size in bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def index_directory(self, directory_path, batch_size=5):
        def generate_documents():
            for root, _, files in os.walk(directory_path):
                for file in files:
                    try:
                        filepath = os.path.join(root, file)
                        file_size = os.path.getsize(filepath)
                        
                        if file_size == 0:
                            print(f"Skipping empty file: {filepath}")
                            continue
                            
                        print(f"\nProcessing: {filepath} ({self.format_size(file_size)})")
                        
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        file_hash = hashlib.md5(content.encode()).hexdigest()
                        chunks = self.chunk_text(content)
                        total_chunks = len(chunks)
                        print(f"Split into {total_chunks} chunks")
                        
                        for chunk_num, chunk in enumerate(chunks):
                            yield {
                                "_index": self.index_name,
                                "_source": {
                                    "content": chunk,
                                    "filename": file,
                                    "filepath": filepath,
                                    "file_hash": file_hash,
                                    "chunk_number": chunk_num,
                                    "total_chunks": total_chunks,
                                    "file_size": file_size,
                                    "indexed_date": time.strftime('%Y-%m-%dT%H:%M:%S')
                                }
                            }
                            
                    except Exception as e:
                        print(f"Error processing {filepath}: {str(e)}")
        
        total_files = sum([len(files) for _, _, files in os.walk(directory_path)])
        print(f"Found {total_files} files to process")
        
        success, failed = 0, 0
        try:
            documents = list(generate_documents())
            total_chunks = len(documents)
            
            with tqdm(total=total_chunks, desc="Indexing chunks") as pbar:
                for i in range(0, total_chunks, batch_size):
                    batch = documents[i:i + batch_size]
                    try:
                        time.sleep(0.1)
                        bulk_response = helpers.bulk(self.es, batch, raise_on_error=False)
                        success += bulk_response[0]
                        failed += len(batch) - bulk_response[0]
                        pbar.update(len(batch))
                        
                    except Exception as e:
                        print(f"\nError processing batch: {str(e)}")
                        failed += len(batch)
                        continue
                        
        except Exception as e:
            print(f"\nError during indexing: {str(e)}")
            raise
                
        print(f"\nIndexing complete. Success: {success}, Failed: {failed}")

    def get_index_stats(self):
        """Get statistics about the current index"""
        try:
            if not self.es.indices.exists(index=self.index_name):
                return {"exists": False}
                
            # Get basic index statistics
            basic_stats = self.es.indices.stats(index=self.index_name)
            # Get document count
            count_result = self.es.count(index=self.index_name)
            # Get index settings and info
            index_info = self.es.indices.get(index=self.index_name)
            
            # Extract size in bytes
            size_in_bytes = basic_stats['indices'][self.index_name]['primaries']['store']['size_in_bytes']
            
            return {
                "exists": True,
                "total_documents": count_result['count'],
                "store_size": self.format_size(size_in_bytes),
                "number_of_shards": index_info[self.index_name]['settings']['index']['number_of_shards'],
                "number_of_replicas": index_info[self.index_name]['settings']['index']['number_of_replicas']
            }
        except Exception as e:
            print(f"Error getting stats: {str(e)}")
            return {"exists": False, "error": str(e)}

# Create template directory and files
os.makedirs('templates', exist_ok=True)
os.makedirs('static', exist_ok=True)

# First, update the CSS file content
with open('static/style.css', 'w') as f:
    f.write("""
[data-theme="dark"] {
    /* Dark theme variables */
    --bg-color: #1a1a1a;
    --text-color: #e1e1e1;
    --card-bg: #2d2d2d;
    --card-border: #404040;
    --highlight-bg: #363636;
    --highlight-border: #0d6efd;
    --code-bg: #363636;
    --muted-text: #a0a0a0;
    --primary-color: #0d6efd;
    --shadow-color: rgba(0,0,0,0.2);
}

body {
    background-color: var(--bg-color);
    color: var(--text-color);
    transition: background-color 0.3s ease, color 0.3s ease;
}

.search-box {
    max-width: 800px;
    margin: 0 auto;
}

.form-control {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border-color: var(--card-border) !important;
}

.form-control:focus {
    box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

.form-select {
    background-color: var(--card-bg) !important;
    color: var(--text-color) !important;
    border-color: var(--card-border) !important;
}

.result-item {
    border: 1px solid var(--card-border);
    border-radius: 4px;
    margin-bottom: 1rem;
    box-shadow: 0 2px 4px var(--shadow-color);
    background-color: var(--card-bg);
}

.highlight {
    margin: 0.5rem 0;
    padding: 0.5rem;
    background-color: var(--highlight-bg);
    border-left: 3px solid var(--highlight-border);
}

.highlight em {
    font-style: normal;
    font-weight: bold;
    background-color: rgba(255, 193, 7, 0.3);
    padding: 0.1rem 0.2rem;
    border-radius: 2px;
}

.card-title {
    color: var(--primary-color);
}

.card-subtitle {
    color: var(--muted-text) !important;
}

.search-tips code {
    background-color: var(--code-bg);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    color: var(--text-color);
}

.card {
    background-color: var(--card-bg);
    border-color: var(--card-border);
}

.text-muted {
    color: var(--muted-text) !important;
}
""")

# Update the HTML template with dark mode toggle
with open('templates/index.html', 'w') as f:
    f.write("""
<!DOCTYPE html>
<html data-theme="dark">
<head>
    <title>sooox' breach browser</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="{{ url_for('static', filename='style.css') }}" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.7.2/font/bootstrap-icons.css">
</head>
<body>
    <div class="container">
        <div class="row mt-5">
            <div class="col">
                <h1 class="text-center mb-4">sooox's breach browser</h1>
                <div class="search-box">
                    <input type="text" id="searchInput" class="form-control form-control-lg" 
                           placeholder="Enter your search query...">
                    <div class="mt-2 d-flex justify-content-between align-items-center">
                        <div>
                            <button onclick="search()" class="btn btn-primary">
                                <i class="bi bi-search"></i> Search
                            </button>
                            <select id="size" class="form-select d-inline-block w-auto ms-2">
                                <option value="10">10 results</option>
                                <option value="25">25 results</option>
                                <option value="50">50 results</option>
                                <option value="100">100 results</option>
                            </select>
                        </div>
                        <div class="search-tips">
                            <button class="btn btn-link" type="button" data-bs-toggle="collapse" 
                                    data-bs-target="#searchTips">
                                Search Tips
                            </button>
                        </div>
                    </div>
                </div>
                
                <div class="collapse mt-3" id="searchTips">
                    <div class="card card-body">
                        <h5>Search Tips:</h5>
                        <ul>
                            <li><code>term1 AND term2</code> - Find documents containing both terms</li>
                            <li><code>"exact phrase"</code> - Find exact phrase matches</li>
                            <li><code>test*</code> - Find words starting with "test"</li>
                            <li><code>term~</code> - Find similar terms (fuzzy search)</li>
                            <li><code>term1 OR term2</code> - Find documents with either term</li>
                            <li><code>NOT term</code> - Exclude documents with this term</li>
                        </ul>
                    </div>
                </div>
                
                <div id="stats" class="mt-3 text-muted"></div>
                
                <div id="results" class="mt-4">
                    <!-- Results will be inserted here -->
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Dark mode toggle functionality
        const themeToggle = document.getElementById('theme-toggle');
        
        // Check for saved theme preference
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        themeToggle.checked = savedTheme === 'dark';
        
        // Theme toggle handler
        themeToggle.addEventListener('change', function() {
            const theme = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });

        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                search();
            }
        });

        function formatFileSize(bytes) {
            const units = ['B', 'KB', 'MB', 'GB'];
            let size = bytes;
            let unitIndex = 0;
            while (size >= 1024 && unitIndex < units.length - 1) {
                size /= 1024;
                unitIndex++;
            }
            return `${size.toFixed(2)} ${units[unitIndex]}`;
        }

        function sanitizeUrl(url) {
            return url.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
                      .replace(/javascript:/gi, '')
                      .replace(/data:/gi, '');
        }

        function search() {
            const query = document.getElementById('searchInput').value;
            const size = document.getElementById('size').value;
            const results = document.getElementById('results');
            const stats = document.getElementById('stats');
            
            results.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"></div></div>';
            
            fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query,
                    size: size
                }),
            })
            .then(response => response.json())
            .then(data => {
                results.innerHTML = '';
                stats.innerHTML = `Found ${data.total} results in ${data.time}ms`;
                
                data.hits.forEach(hit => {
                    const resultDiv = document.createElement('div');
                    resultDiv.className = 'result-item card mb-3';
                    
                    let highlights = '';
                    if (hit.highlights) {
                        highlights = hit.highlights.map(h => {
                            const sanitizedHighlight = sanitizeUrl(h);
                            return `<div class="highlight">${sanitizedHighlight}</div>`;
                        }).join('');
                    }
                    
                    resultDiv.innerHTML = `
                        <div class="card-body">
                            <h5 class="card-title">
                                <i class="bi bi-file-text"></i> 
                                ${hit.filename}
                            </h5>
                            <h6 class="card-subtitle mb-2">
                                <i class="bi bi-folder"></i> ${hit.filepath}<br>
                                <i class="bi bi-layers"></i> Chunk ${hit.chunk_number + 1} of ${hit.total_chunks} | 
                                <i class="bi bi-file-binary"></i> ${formatFileSize(hit.file_size)} |
                                <i class="bi bi-star"></i> Score: ${hit.score}
                            </h6>
                            <div class="highlights mt-2">
                                ${highlights}
                            </div>
                        </div>
                    `;
                    
                    results.appendChild(resultDiv);
                });
                
                if (data.hits.length === 0) {
                    results.innerHTML = '<div class="alert alert-info">No results found</div>';
                }
            })
            .catch(error => {
                results.innerHTML = '<div class="alert alert-danger">An error occurred while searching</div>';
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
""")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query', '')
    size = int(data.get('size', 10))
    
    search_query = {
        "query": {
            "query_string": {
                "query": query,
                "fields": ["content"],
                "default_operator": "AND"
            }
        },
        "highlight": {
            "fields": {
                "content": {
                    "fragment_size": 150,
                    "number_of_fragments": 3,
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"],
                    "boundary_scanner": "sentence",
                    "boundary_scanner_locale": "en-US",
                    "fragment_offset": 0,
                    "no_match_size": 0
                }
            },
            "boundary_max_scan": 50
        },
        "_source": ["filename", "filepath", "chunk_number", "total_chunks", "file_size"]
    }
    
    try:
        start_time = time.time()
        response = es.search(index="text_documents", body=search_query, size=size)
        search_time = int((time.time() - start_time) * 1000)
        
        hits = []
        for hit in response['hits']['hits']:
            # Process highlights to clean up the display
            highlights = hit.get('highlight', {}).get('content', [])
            cleaned_highlights = []
            
            for highlight in highlights:
                # Split by newlines and only keep lines containing highlighted terms
                lines = highlight.split('\n')
                relevant_lines = [line.strip() for line in lines if '<em>' in line]
                if relevant_lines:
                    cleaned_highlights.extend(relevant_lines)
            
            result = {
                'filename': hit['_source']['filename'],
                'filepath': hit['_source']['filepath'],
                'chunk_number': hit['_source']['chunk_number'],
                'total_chunks': hit['_source']['total_chunks'],
                'file_size': hit['_source']['file_size'],
                'score': round(hit['_score'], 2),
                'highlights': cleaned_highlights
            }
            hits.append(result)
        
        return jsonify({
            'hits': hits,
            'total': response['hits']['total']['value'],
            'time': search_time
        })
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # First, set up the search engine
    print("Initializing search engine...")
    es = Elasticsearch([{'host': 'localhost', 'port': 9200}])
    engine = TextSearchEngine()
    
    # Get and display current index statistics
    stats = engine.get_index_stats()
    if stats.get("exists"):
        print("\nCurrent Index Statistics:")
        print(f"Total Documents: {stats['total_documents']}")
        print(f"Index Size: {stats['store_size']}")
        print(f"Number of Shards: {stats['number_of_shards']}")
        print(f"Number of Replicas: {stats['number_of_replicas']}")
    else:
        print("\nNo existing index found")
    
    # Set data directory path
    data_dir = 'data'
    
    if not os.path.exists(data_dir):
        print(f"Error: Data directory not found at {data_dir}")
        sys.exit(1)
        
    # Ask user if they want to reindex
    while True:
        reindex = input("\nDo you want to reindex the data? (yes/no): ").lower()
        if reindex in ['yes', 'no']:
            break
        print("Please enter 'yes' or 'no'")
    
    if reindex == 'yes':
        try:
            print("Deleting existing index...")
            engine.delete_index()
            print("Creating new index...")
            engine.create_index()
            print(f"Indexing files from: {data_dir}")
            engine.index_directory(data_dir)
            
            # Show updated stats after indexing
            print("\nUpdated Index Statistics:")
            stats = engine.get_index_stats()
            if stats.get("exists"):
                print(f"Total Documents: {stats['total_documents']}")
                print(f"Index Size: {stats['store_size']}")
                print(f"Number of Shards: {stats['number_of_shards']}")
                print(f"Number of Replicas: {stats['number_of_replicas']}")
        except Exception as e:
            print(f"Error during indexing: {str(e)}")
            sys.exit(1)
    
    print("\nStarting web interface on http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
