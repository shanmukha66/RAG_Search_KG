import React from 'react';
import { Typography, Paper, Box } from '@mui/material';

function Home() {
  return (
    <Box sx={{ maxWidth: 800, mx: 'auto' }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Welcome to Multimodal RAG System
        </Typography>
        <Typography variant="body1" paragraph>
          This system supports advanced retrieval-augmented generation across multiple content types:
        </Typography>
        <Typography component="ul" sx={{ pl: 3 }}>
          <li>Text documents and PDFs</li>
          <li>Images with text extraction</li>
          <li>Audio transcription and analysis</li>
          <li>Video content processing</li>
        </Typography>
        <Typography variant="body1" sx={{ mt: 2 }}>
          Use the navigation menu to upload new content or search through the existing knowledge base.
        </Typography>
      </Paper>
    </Box>
  );
}

export default Home; 