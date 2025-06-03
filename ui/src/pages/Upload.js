import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

function Upload() {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleDrop = async (event) => {
    event.preventDefault();
    const files = event.dataTransfer?.files || event.target.files;
    
    if (!files.length) return;

    setUploading(true);
    setError(null);
    setSuccess(false);

    try {
      // TODO: Implement actual file upload logic here
      // This is where you'll integrate with your Python backend
      console.log('Files to upload:', files);
      
      // Simulate upload delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setSuccess(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const preventDefault = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto' }}>
      <Paper
        sx={{
          p: 4,
          textAlign: 'center',
          cursor: uploading ? 'wait' : 'pointer',
        }}
        onDrop={handleDrop}
        onDragOver={preventDefault}
        onDragEnter={preventDefault}
      >
        <input
          type="file"
          id="file-upload"
          multiple
          style={{ display: 'none' }}
          onChange={handleDrop}
        />
        <label htmlFor="file-upload">
          <Box
            sx={{
              border: '2px dashed #ccc',
              borderRadius: 2,
              p: 4,
              '&:hover': {
                borderColor: 'primary.main',
              },
            }}
          >
            <CloudUploadIcon sx={{ fontSize: 48, mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drag and drop files here
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              or
            </Typography>
            <Button variant="contained" component="span" disabled={uploading}>
              Browse Files
            </Button>
          </Box>
        </label>

        {uploading && (
          <Box sx={{ mt: 2 }}>
            <CircularProgress />
          </Box>
        )}

        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mt: 2 }}>
            Files uploaded successfully!
          </Alert>
        )}
      </Paper>
    </Box>
  );
}

export default Upload; 