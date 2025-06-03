import React from 'react';
import {
  Box,
  VStack,
  Text,
  Image,
  Badge,
  Grid,
  GridItem,
  Heading,
} from '@chakra-ui/react';

interface ResultProps {
  results: Array<{
    id: string;
    content_type: string;
    metadata: {
      title?: string;
      description?: string;
      image_url?: string;
      text_content?: string;
    };
    score: number;
  }>;
}

export function Results({ results }: ResultProps) {
  if (!results.length) {
    return (
      <Box textAlign="center" py={8}>
        <Text color="gray.500">No results found</Text>
      </Box>
    );
  }

  return (
    <VStack spacing={4} align="stretch">
      <Heading size="md" mb={4}>
        Search Results ({results.length})
      </Heading>
      <Grid templateColumns="repeat(auto-fill, minmax(300px, 1fr))" gap={6}>
        {results.map((result) => (
          <GridItem
            key={result.id}
            bg="white"
            p={4}
            borderRadius="lg"
            boxShadow="sm"
            transition="all 0.2s"
            _hover={{ boxShadow: 'md' }}
          >
            <VStack align="stretch" spacing={3}>
              <Badge colorScheme={getColorScheme(result.content_type)}>
                {result.content_type}
              </Badge>
              
              {result.metadata.image_url && (
                <Image
                  src={result.metadata.image_url}
                  alt={result.metadata.title || 'Result image'}
                  objectFit="cover"
                  borderRadius="md"
                  maxH="200px"
                />
              )}
              
              {result.metadata.title && (
                <Heading size="sm">{result.metadata.title}</Heading>
              )}
              
              {result.metadata.description && (
                <Text noOfLines={3} color="gray.600">
                  {result.metadata.description}
                </Text>
              )}
              
              {result.metadata.text_content && (
                <Text noOfLines={4} fontSize="sm" color="gray.500">
                  {result.metadata.text_content}
                </Text>
              )}
              
              <Text fontSize="sm" color="gray.400">
                Relevance: {(result.score * 100).toFixed(1)}%
              </Text>
            </VStack>
          </GridItem>
        ))}
      </Grid>
    </VStack>
  );
}

function getColorScheme(contentType: string): string {
  switch (contentType) {
    case 'text':
      return 'blue';
    case 'image':
      return 'green';
    case 'video':
      return 'purple';
    default:
      return 'gray';
  }
} 