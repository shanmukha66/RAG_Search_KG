import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from 'react-query';
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
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';

const queryTypes = [
  { value: 'factual', label: 'Factual' },
  { value: 'summarization', label: 'Summarization' },
  { value: 'semantic_linkage', label: 'Semantic Linkage' },
  { value: 'reasoning', label: 'Reasoning' },
];

const Search: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState('factual');
  const [error, setError] = useState<string | null>(null);

  const searchMutation = useMutation(
    async (data: { text: string; type: string }) => {
      const response = await axios.post('http://localhost:8000/api/query', data);
      return response.data;
    },
    {
      onSuccess: (data) => {
        navigate('/results', {
          state: {
            query,
            queryType,
            results: data,
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
        />

        <FormControl fullWidth sx={{ mb: 2 }}>
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

        <Button
          fullWidth
          variant="contained"
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