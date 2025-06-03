import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { useMutation } from 'react-query';
import axios from 'axios';
import {
  Box,
  Paper,
  Typography,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  CircularProgress,
  Alert,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  InsertDriveFile as FileIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress?: number;
  error?: string;
}

const Upload: React.FC = () => {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation(
    async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post(
        'http://localhost:8000/api/upload',
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );
      return response.data;
    },
    {
      onError: (error: any) => {
        setError(
          error.response?.data?.detail ||
            'An error occurred while uploading files'
        );
      },
    }
  );

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);
    const newFiles = acceptedFiles.map((file) => ({
      file,
      status: 'pending' as const,
    }));
    setFiles((prev) => [...prev, ...newFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.gif'],
      'video/*': ['.mp4', '.avi', '.mov'],
      'audio/*': ['.mp3', '.wav', '.ogg'],
      'application/pdf': ['.pdf'],
      'text/plain': ['.txt'],
    },
    disabled: uploadMutation.isLoading,
  });

  const handleUpload = async () => {
    setError(null);
    
    for (const file of files) {
      if (file.status === 'pending') {
        try {
          // Update status to uploading
          setFiles((prev) =>
            prev.map((f) =>
              f === file ? { ...f, status: 'uploading' } : f
            )
          );

          // Upload file
          await uploadMutation.mutateAsync(file.file);

          // Update status to success
          setFiles((prev) =>
            prev.map((f) =>
              f === file ? { ...f, status: 'success' } : f
            )
          );
        } catch (error: any) {
          // Update status to error
          setFiles((prev) =>
            prev.map((f) =>
              f === file
                ? {
                    ...f,
                    status: 'error',
                    error:
                      error.response?.data?.detail ||
                      'Error uploading file',
                  }
                : f
            )
          );
        }
      }
    }
  };

  const getFileIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'uploading':
        return <CircularProgress size={24} />;
      default:
        return <FileIcon />;
    }
  };

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4 }}>
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: 'center',
          cursor: uploadMutation.isLoading ? 'not-allowed' : 'pointer',
          bgcolor: isDragActive ? 'action.hover' : 'background.paper',
          border: '2px dashed',
          borderColor: isDragActive ? 'primary.main' : 'divider',
          opacity: uploadMutation.isLoading ? 0.7 : 1,
        }}
      >
        <input {...getInputProps()} />
        <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
        <Typography variant="h6" gutterBottom>
          {uploadMutation.isLoading
            ? 'Upload in progress...'
            : 'Drag and drop files here'}
        </Typography>
        <Typography color="textSecondary">
          {uploadMutation.isLoading
            ? 'Please wait while we process your files'
            : 'or click to select files'}
        </Typography>
      </Paper>

      {files.length > 0 && (
        <Paper sx={{ mt: 3, p: 2 }}>
          <List>
            {files.map((file, index) => (
              <ListItem key={index}>
                <ListItemIcon>{getFileIcon(file.status)}</ListItemIcon>
                <ListItemText
                  primary={file.file.name}
                  secondary={
                    <>
                      {`${(file.file.size / 1024 / 1024).toFixed(2)} MB`}
                      {file.error && (
                        <Typography color="error" variant="caption" display="block">
                          {file.error}
                        </Typography>
                      )}
                    </>
                  }
                />
              </ListItem>
            ))}
          </List>
          <Box sx={{ mt: 2, textAlign: 'right' }}>
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={
                uploadMutation.isLoading ||
                files.every((f) => f.status === 'success')
              }
            >
              {uploadMutation.isLoading ? 'Uploading...' : 'Upload Files'}
            </Button>
          </Box>
        </Paper>
      )}
    </Box>
  );
};

export default Upload; 