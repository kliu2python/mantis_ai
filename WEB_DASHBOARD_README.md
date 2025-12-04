# Mantis AI Web Dashboard

A React-based web dashboard for viewing, searching, and analyzing Mantis issues with AI-powered capabilities.

## Features

### 1. Keyword Search
- Search issues by keywords across all fields
- Filter by status, category, and other attributes
- Real-time search results

### 2. AI-Powered Semantic Search
- Natural language queries using embeddings
- Find semantically similar issues
- Ranking by relevance scores

### 3. Similar Issues Finder
- Find issues similar to a specific issue ID
- Useful for identifying duplicates or related issues
- Cosine similarity ranking

### 4. Analytics Dashboard
- Status distribution charts
- Category analysis
- Trend visualization
- Project statistics

### 5. Multi-Project Support
- Switch between different Mantis projects
- Project-specific analytics and search
- Consistent interface across all projects

## Architecture

### Frontend (React)
```
src/
├── components/     # Reusable UI components
├── pages/         # Page components for different routes
├── services/      # API service layer
├── hooks/         # Custom React hooks
└── utils/         # Utility functions
```

### Backend (Python Flask)
```
api/
├── server.py      # Main Flask application
├── requirements.txt # Python dependencies
└── utils/         # Helper functions
```

## Prerequisites

### Frontend
- Node.js 14+
- npm or yarn

### Backend
- Python 3.8+
- SQLite database with Mantis issues
- AI libraries (sentence-transformers, scikit-learn)

## Installation

### Backend API
```bash
cd api
pip install -r requirements.txt
python server.py
```

### Frontend Dashboard
```bash
cd web_dashboard
npm install
npm start
```

## API Endpoints

### Projects
- `GET /api/projects` - List all available projects

### Issues
- `GET /api/issues/<project_id>` - Get issues with filtering
- `POST /api/issues/<project_id>/search` - Keyword search
- `POST /api/issues/<project_id>/ai-search` - AI semantic search
- `GET /api/issues/<project_id>/<issue_id>/similar` - Find similar issues

### Analytics
- `GET /api/analytics/<project_id>` - Project analytics

## AI Features

### Semantic Search
Uses sentence transformers to create embeddings of issue content and enables semantic search:

1. Issues are converted to text representations
2. Embeddings are generated using all-MiniLM-L6-v2 model
3. Queries are embedded and compared using cosine similarity
4. Results are ranked by similarity score

### Similar Issues
Finds issues similar to a given issue by:

1. Comparing issue embeddings
2. Calculating pairwise similarities
3. Ranking by cosine similarity
4. Returning top matches

## Development

### Adding New Features

1. **Frontend**: Add components in `src/components/` and pages in `src/pages/`
2. **Backend**: Add routes in `api/server.py` and utilities in `api/utils/`
3. **AI Models**: Extend embedding functionality in the server

### Customization

- **Styling**: Modify themes in `src/styles/`
- **Search Logic**: Update search algorithms in backend
- **Analytics**: Add new charts and metrics in analytics components

## Deployment

### Backend
```bash
# Production deployment
export FLASK_ENV=production
gunicorn -w 4 server:app
```

### Frontend
```bash
# Build for production
npm run build
# Serve build folder with nginx, Apache, etc.
```

## Environment Variables

Create a `.env` file in the api directory:
```env
DATABASE_PATH=./mantis_data.db
OPENAI_API_KEY=your-openai-api-key
FLASK_ENV=development
```

## Troubleshooting

### Database Connection Issues
- Verify `mantis_data.db` exists in the correct location
- Check file permissions
- Ensure SQLite is accessible

### AI Model Loading Slow
- First-time model download may take several minutes
- Models are cached locally after first download
- Ensure adequate disk space and internet connectivity

### Search Results Empty
- Verify project ID is correct
- Check that issues exist in the database
- Confirm search terms match issue content