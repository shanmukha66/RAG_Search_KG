import React from 'react';
import { useDropzone } from 'react-dropzone';
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
import useFileUpload from '../hooks/useFileUpload';

const Upload: React.FC = () => {
  const { uploadFile, uploadState, isUploading, reset } = useFileUpload();

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (acceptedFiles) => {
      acceptedFiles.forEach((file) => uploadFile(file));
    },
  });

  return (
    <Box sx={{ maxWidth: 800, mx: 'auto', mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Upload Files
        </Typography>

        <Box
          {...getRootProps()}
          sx={{
            border: '2px dashed',
            borderColor: isDragActive ? 'primary.main' : 'grey.300',
            borderRadius: 2,
            p: 4,
            textAlign: 'center',
            cursor: 'pointer',
            mb: 3,
            '&:hover': {
              borderColor: 'primary.main',
              bgcolor: 'action.hover',
            },
          }}
        >
          <input {...getInputProps()} />
          <CloudUploadIcon sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            {isDragActive
              ? 'Drop files here'
              : 'Drag and drop files here, or click to select files'}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Supported formats: PDF, DOC, DOCX, TXT, JPG, PNG, MP3, MP4
          </Typography>
        </Box>

        {Object.entries(uploadState).length > 0 && (
          <>
            <List>
              {Object.entries(uploadState).map(([fileName, state]) => (
                <ListItem key={fileName}>
                  <ListItemIcon>
                    {state.error ? (
                      <ErrorIcon color="error" />
                    ) : state.progress === 100 ? (
                      <CheckIcon color="success" />
                    ) : (
                      <FileIcon />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={fileName}
                    secondary={
                      state.error
                        ? state.error
                        : `Progress: ${state.progress}%`
                    }
                  />
                  {state.progress < 100 && !state.error && (
                    <CircularProgress
                      variant="determinate"
                      value={state.progress}
                      size={24}
                    />
                  )}
                </ListItem>
              ))}
            </List>

            <Button
              onClick={reset}
              variant="outlined"
              color="primary"
              sx={{ mt: 2 }}
            >
              Clear List
            </Button>
          </>
        )}

        {isUploading && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Uploading files...
          </Alert>
        )}
      </Paper>
    </Box>
  );
};

export default Upload; 