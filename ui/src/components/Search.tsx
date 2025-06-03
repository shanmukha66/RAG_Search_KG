import React, { useState } from 'react';
import {
  Box,
  Input,
  Button,
  HStack,
  Select,
  FormControl,
  FormLabel,
} from '@chakra-ui/react';
import { useQuery } from 'react-query';
import { api } from '../api';

interface SearchProps {
  onResults: (results: any[]) => void;
}

export function Search({ onResults }: SearchProps) {
  const [query, setQuery] = useState('');
  const [contentType, setContentType] = useState('all');

  const { refetch, isLoading } = useQuery(
    ['search', query, contentType],
    async () => {
      if (!query) return { results: [] };
      const response = await api.post('/search', {
        query,
        content_type: contentType === 'all' ? null : contentType,
        limit: 10,
        expand_results: true,
      });
      onResults(response.data.results);
      return response.data;
    },
    {
      enabled: false,
    }
  );

  const handleSearch = () => {
    if (query.trim()) {
      refetch();
    }
  };

  return (
    <Box>
      <FormControl>
        <FormLabel>Search Query</FormLabel>
        <HStack spacing={4}>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter your search query..."
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
          />
          <Select
            value={contentType}
            onChange={(e) => setContentType(e.target.value)}
            w="200px"
          >
            <option value="all">All Types</option>
            <option value="text">Text</option>
            <option value="image">Image</option>
            <option value="video">Video</option>
          </Select>
          <Button
            colorScheme="blue"
            onClick={handleSearch}
            isLoading={isLoading}
            loadingText="Searching..."
          >
            Search
          </Button>
        </HStack>
      </FormControl>
    </Box>
  );
} 