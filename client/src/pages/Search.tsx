import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation } from 'react-query';
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
import api, { QueryRequest } from '../services/api';

const queryTypes = [
  { value: 'factual', label: 'Factual' },
  { value: 'summarization', label: 'Summarization' },
  { value: 'semantic_linkage', label: 'Semantic Linkage' },
  { value: 'reasoning', label: 'Reasoning' },
] as const;

type QueryType = typeof queryTypes[number]['value'];

const Search: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [queryType, setQueryType] = useState<QueryType>('factual');
  const [error, setError] = useState<string | null>(null);

  const queryMutation = useMutation(
    (queryRequest: QueryRequest) => api.processQuery(queryRequest),
    {
      onSuccess: (data) => {
        navigate('/results', { state: { results: data } });
      },
      onError: (error) => {
        setError(error instanceof Error ? error.message : 'An error occurred');
      },
    }
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    queryMutation.mutate({
      text: query,
      type: queryType,
    });
  };

  return (
    <Box
      component="form"
      onSubmit={handleSubmit}
      sx={{
        maxWidth: 800,
        mx: 'auto',
        mt: 4,
      }}
    >
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Search Knowledge Base
        </Typography>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <FormControl fullWidth sx={{ mb: 3 }}>
          <TextField
            label="Enter your query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            multiline
            rows={3}
            variant="outlined"
          />
        </FormControl>

        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Query Type</InputLabel>
          <Select
            value={queryType}
            label="Query Type"
            onChange={(e) => setQueryType(e.target.value as QueryType)}
          >
            {queryTypes.map((type) => (
              <MenuItem key={type.value} value={type.value}>
                {type.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Button
          type="submit"
          variant="contained"
          size="large"
          startIcon={queryMutation.isLoading ? <CircularProgress size={20} /> : <SearchIcon />}
          disabled={queryMutation.isLoading}
          fullWidth
        >
          {queryMutation.isLoading ? 'Searching...' : 'Search'}
        </Button>
      </Paper>
    </Box>
  );
};

export default Search; 