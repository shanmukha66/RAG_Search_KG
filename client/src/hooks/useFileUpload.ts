import { useState } from 'react';
import { useMutation } from 'react-query';
import api from '../services/api';

interface FileUploadState {
  progress: number;
  error: string | null;
}

export const useFileUpload = () => {
  const [uploadState, setUploadState] = useState<Record<string, FileUploadState>>({});

  const uploadMutation = useMutation(
    async (file: File) => {
      setUploadState((prev) => ({
        ...prev,
        [file.name]: { progress: 0, error: null },
      }));
      
      try {
        const result = await api.uploadFile(file);
        setUploadState((prev) => ({
          ...prev,
          [file.name]: { progress: 100, error: null },
        }));
        return result;
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        setUploadState((prev) => ({
          ...prev,
          [file.name]: { progress: 0, error: errorMessage },
        }));
        throw error;
      }
    }
  );

  return {
    uploadFile: uploadMutation.mutate,
    uploadState,
    isUploading: uploadMutation.isLoading,
    reset: () => setUploadState({}),
  };
};

export default useFileUpload; 