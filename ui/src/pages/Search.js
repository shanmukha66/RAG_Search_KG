import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  CircularProgress,
  Card,
  CardContent,
  Stack,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

function Search() {
  const [query, setQuery] = useState('');
  const [searching, setSearching] = useState(false);
  const [results, setResults] = useState([]);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSearching(true);
    try {
      // TODO: Implement actual search logic here
      // This is where you'll integrate with your Python backend
      console.log('Searching for:', query);
      
      // Simulate search delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock results
      setResults([
        {
          id: 1,
          type: 'text',
          title: 'Sample Document',
          content: 'This is a sample search result...',
          confidence: 0.95,
        },
        // Add more mock results as needed
      ]);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setSearching(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Paper sx={{ p: 4 }}>
        <form onSubmit={handleSearch}>
          <Stack direction="row" spacing={2}>
            <TextField
              fullWidth
              label="Search Query"
              variant="outlined"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={searching}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={searching || !query.trim()}
              startIcon={searching ? <CircularProgress size={20} /> : <SearchIcon />}
            >
              Search
            </Button>
          </Stack>
        </form>

        {results.length > 0 && (
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" gutterBottom>
              Search Results
            </Typography>
            <Stack spacing={2}>
              {results.map((result) => (
                <Card key={result.id}>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      {result.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Type: {result.type}
                    </Typography>
                    <Typography variant="body1" sx={{ mt: 1 }}>
                      {result.content}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Confidence: {(result.confidence * 100).toFixed(1)}%
                    </Typography>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </Box>
        )}
      </Paper>
    </Box>
  );
}

export default Search; 