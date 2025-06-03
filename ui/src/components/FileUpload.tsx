import React, { useCallback } from 'react';
import { Box, Button, Text, useToast, VStack } from '@chakra-ui/react';
import { useDropzone } from 'react-dropzone';
import { useMutation } from 'react-query';
import { api } from '../api';

export function FileUpload() {
  const toast = useToast();
  
  const uploadMutation = useMutation(
    async (file: File) => {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('content_type', file.type.startsWith('image/') ? 'image' : 'text');
      return api.post('/ingest/file', formData);
    },
    {
      onSuccess: () => {
        toast({
          title: 'File uploaded successfully',
          status: 'success',
          duration: 3000,
        });
      },
      onError: (error) => {
        toast({
          title: 'Upload failed',
          description: error.message,
          status: 'error',
          duration: 5000,
        });
      },
    }
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      acceptedFiles.forEach((file) => uploadMutation.mutate(file));
    },
    [uploadMutation]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/*': ['.txt', '.md', '.pdf'],
      'image/*': ['.jpg', '.jpeg', '.png'],
      'video/*': ['.mp4', '.avi', '.mov'],
    },
  });

  return (
    <Box>
      <VStack
        {...getRootProps()}
        p={6}
        bg={isDragActive ? 'blue.50' : 'white'}
        border="2px dashed"
        borderColor={isDragActive ? 'blue.500' : 'gray.200'}
        borderRadius="lg"
        cursor="pointer"
        transition="all 0.2s"
        _hover={{ borderColor: 'blue.500' }}
      >
        <input {...getInputProps()} />
        <Text color="gray.500">
          {isDragActive
            ? 'Drop the files here...'
            : 'Drag and drop files here, or click to select files'}
        </Text>
        <Button colorScheme="blue" size="sm">
          Select Files
        </Button>
      </VStack>
    </Box>
  );
} 