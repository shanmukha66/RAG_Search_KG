import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from 'react-query';
import axios from 'axios';
import {
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Paper,
  Typography,
  Alert,
  CircularProgress,
  Tabs,
  Tab,
  Grid,
  Link,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

const queryTypes = [
  { value: 'factual', label: 'Factual' },
  { value: 'vector', label: 'Vector Search' },
  { value: 'graph', label: 'Graph Search' },
];

const Search: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState('factual');
  const [error, setError] = useState<string | null>(null);
  const [searchLimit, setSearchLimit] = useState(10);

  // Health check query
  const healthQuery = useQuery('health', async () => {
    const response = await axios.get('http://localhost:8000/api/health');
    return response.data;
  });

  const searchMutation = useMutation(
    async (data: { text: string; type: string; limit?: number }) => {
      let endpoint = 'http://localhost:8000/api/query';
      
      if (data.type === 'vector') {
        endpoint = 'http://localhost:8000/api/vector-search';
      } else if (data.type === 'graph') {
        endpoint = 'http://localhost:8000/api/graph-search';
        return axios.post(endpoint, { entity: data.text });
      }
      
      return axios.post(endpoint, data);
    },
    {
      onSuccess: (response) => {
        navigate('/results', {
          state: {
            query,
            queryType,
            results: response.data,
          },
        });
      },
      onError: (error: any) => {
        setError(
          error.response?.data?.detail ||
            'An error occurred while processing your query'
        );
      },
    }
  );

  const handleSearch = async () => {
    setError(null);
    searchMutation.mutate({
      text: query,
      type: queryType,
      limit: searchLimit,
    });
  };

  return (
    <Box
      component={Paper}
      sx={{
        p: 4,
        maxWidth: 800,
        mx: 'auto',
        mt: 4,
      }}
    >
      <Typography variant="h4" gutterBottom>
        Search
      </Typography>

      {/* Health Status */}
      {healthQuery.data && (
        <Box sx={{ mb: 3 }}>
          <Alert severity={
            healthQuery.data.neo4j === 'healthy' && 
            healthQuery.data.qdrant === 'healthy' 
              ? 'success' 
              : 'warning'
          }>
            Neo4j: {healthQuery.data.neo4j} (
              <Link href="http://localhost:7475" target="_blank" rel="noopener">
                Browser
              </Link>
            ), 
            Qdrant: {healthQuery.data.qdrant} (
              <Link href="http://localhost:6333/dashboard" target="_blank" rel="noopener">
                Dashboard
              </Link>
            )
          </Alert>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          label="Enter your query"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          multiline
          rows={3}
          sx={{ mb: 2 }}
          disabled={searchMutation.isLoading}
          error={!!error}
          helperText={
            queryType === 'graph' 
              ? "Enter entity name for graph search" 
              : "Enter your search query"
          }
        />

        <Grid container spacing={2}>
          <Grid item xs={8}>
            <FormControl fullWidth>
              <InputLabel>Query Type</InputLabel>
              <Select
                value={queryType}
                label="Query Type"
                onChange={(e) => setQueryType(e.target.value)}
                disabled={searchMutation.isLoading}
              >
                {queryTypes.map((type) => (
                  <MenuItem key={type.value} value={type.value}>
                    {type.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Grid>
          <Grid item xs={4}>
            <TextField
              fullWidth
              type="number"
              label="Result Limit"
              value={searchLimit}
              onChange={(e) => setSearchLimit(Number(e.target.value))}
              disabled={searchMutation.isLoading || queryType === 'graph'}
            />
          </Grid>
        </Grid>

        <Button
          fullWidth
          variant="contained"
          sx={{ mt: 2 }}
          startIcon={
            searchMutation.isLoading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <SearchIcon />
            )
          }
          onClick={handleSearch}
          disabled={!query.trim() || searchMutation.isLoading}
        >
          {searchMutation.isLoading ? 'Searching...' : 'Search'}
        </Button>
      </Box>
    </Box>
  );
};

export default Search; 