import React, { useState } from 'react';
import { ChakraProvider, Box, VStack, Container, Heading } from '@chakra-ui/react';
import { QueryClient, QueryClientProvider } from 'react-query';
import { FileUpload } from './components/FileUpload';
import { Search } from './components/Search';
import { Results } from './components/Results';
import { Navigation } from './components/Navigation';
import { theme } from './theme';

const queryClient = new QueryClient();

function App() {
  const [searchResults, setSearchResults] = useState([]);

  return (
    <ChakraProvider theme={theme}>
      <QueryClientProvider client={queryClient}>
        <Box minH="100vh" bg="gray.50">
          <Navigation />
          <Container maxW="container.xl" py={8}>
            <VStack spacing={8} align="stretch">
              <Heading as="h1" size="xl" textAlign="center">
                Enterprise RAG System
              </Heading>
              
              <FileUpload />
              <Search onResults={setSearchResults} />
              <Results results={searchResults} />
            </VStack>
          </Container>
        </Box>
      </QueryClientProvider>
    </ChakraProvider>
  );
}

export default App; 