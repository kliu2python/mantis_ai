# Lightweight Mantis Web Dashboard

A React-based web dashboard for viewing, searching, and analyzing Mantis issues without heavy AI dependencies.

## Features

### 1. Keyword Search
- Search issues by keywords across all fields
- Filter by status, category, and other attributes
- Real-time search results

### 2. Similar Issues Finder
- Find issues similar to a specific issue ID
- Uses simple text similarity algorithm
- Useful for identifying duplicates or related issues

### 3. Analytics Dashboard
- Status distribution charts
- Category analysis
- Trend visualization
- Project statistics

### 4. Multi-Project Support
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
├── server_light.py  # Main Flask application (lightweight)
├── requirements_light.txt # Python dependencies (no AI)
└── utils/            # Helper functions
```

## Prerequisites

### Frontend
- Node.js 14+
- npm or yarn

### Backend
- Python 3.8+
- SQLite database with Mantis issues

## Installation

### Backend API
```bash
cd api
pip install -r requirements_light.txt
python server_light.py
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
- `GET /api/issues/<project_id>/<issue_id>/similar` - Find similar issues

### Analytics
- `GET /api/analytics/<project_id>` - Project analytics

## Similar Issues Algorithm

The lightweight version uses a simple text similarity algorithm:

1. **Text Representation**: Combines summary, description, steps_to_reproduce, and category fields
2. **Preprocessing**: Converts to lowercase, removes special characters
3. **Similarity Calculation**: Uses Jaccard similarity on word sets
4. **Ranking**: Orders results by similarity score

While not as sophisticated as embedding-based approaches, it's:
- Much faster to compute
- Doesn't require downloading large AI models
- Still effective for finding similar issues
- Uses minimal system resources

## Development

### Adding New Features

1. **Frontend**: Add components in `src/components/` and pages in `src/pages/`
2. **Backend**: Add routes in `api/server_light.py` and utilities in `api/utils/`

### Customization

- **Styling**: Modify themes in `src/styles/`
- **Search Logic**: Update search algorithms in backend
- **Analytics**: Add new charts and metrics in analytics components

## Deployment

### Backend
```bash
# Production deployment
export FLASK_ENV=production
gunicorn -w 4 server_light:app
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
FLASK_ENV=development
```

## Troubleshooting

### Database Connection Issues
- Verify `mantis_data.db` exists in the correct location
- Check file permissions
- Ensure SQLite is accessible

### Search Results Empty
- Verify project ID is correct
- Check that issues exist in the database
- Confirm search terms match issue content

### Performance Issues
- The lightweight version is optimized for speed
- For large databases, consider adding database indexes
- Pagination limits results to 100 per page by default

## Future Enhancements

You can extend this lightweight version by:

1. **Adding Full-Text Search**: Integrate SQLite FTS5 for better search
2. **Improving Similarity**: Add more sophisticated text matching algorithms
3. **Adding Caching**: Implement Redis caching for frequent queries
4. **Database Optimization**: Add indexes for common query fields
5. **Export Features**: Add CSV/PDF export capabilities

The modular design makes it easy to add these features incrementally.