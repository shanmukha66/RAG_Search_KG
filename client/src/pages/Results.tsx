import React from 'react';
import { useLocation, Navigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Stack,
  LinearProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
} from '@mui/material';
import {
  Description as DocumentIcon,
  Image as ImageIcon,
  Audiotrack as AudioIcon,
  VideoLibrary as VideoIcon,
} from '@mui/icons-material';
import { QueryResponse } from '../services/api';

interface LocationState {
  results: QueryResponse;
}

const getSourceIcon = (type: string) => {
  switch (type.toLowerCase()) {
    case 'text':
    case 'pdf':
    case 'doc':
      return <DocumentIcon />;
    case 'image':
      return <ImageIcon />;
    case 'audio':
      return <AudioIcon />;
    case 'video':
      return <VideoIcon />;
    default:
      return <DocumentIcon />;
  }
};

const Results: React.FC = () => {
  const location = useLocation();
  const state = location.state as LocationState;

  if (!state?.results) {
    return <Navigate to="/" replace />;
  }

  const { answer, confidence, sources, cross_references, evaluation } = state.results;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto', mt: 4 }}>
      <Paper sx={{ p: 4 }}>
        <Typography variant="h4" gutterBottom>
          Results
        </Typography>

        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Answer
            </Typography>
            <Typography variant="body1" paragraph>
              {answer}
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <Typography variant="subtitle2">Confidence:</Typography>
              <Box sx={{ flexGrow: 1, mr: 2 }}>
                <LinearProgress
                  variant="determinate"
                  value={confidence * 100}
                  sx={{ height: 8, borderRadius: 4 }}
                />
              </Box>
              <Typography variant="body2">{Math.round(confidence * 100)}%</Typography>
            </Stack>
          </CardContent>
        </Card>

        <Typography variant="h6" gutterBottom>
          Sources
        </Typography>
        <List>
          {sources.map((source, index) => (
            <ListItem key={index}>
              <ListItemIcon>{getSourceIcon(source.type)}</ListItemIcon>
              <ListItemText
                primary={source.title}
                secondary={`Relevance: ${Math.round(source.relevance * 100)}%`}
              />
              <Chip
                label={source.type.toUpperCase()}
                size="small"
                sx={{ ml: 2 }}
              />
            </ListItem>
          ))}
        </List>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h6" gutterBottom>
          Cross References
        </Typography>
        <List>
          {cross_references.map((ref, index) => (
            <ListItem key={index}>
              <ListItemText
                primary={ref.text}
                secondary={`Source: ${ref.source} | Confidence: ${Math.round(
                  ref.confidence * 100
                )}%`}
              />
            </ListItem>
          ))}
        </List>

        <Divider sx={{ my: 4 }} />

        <Typography variant="h6" gutterBottom>
          Evaluation Metrics
        </Typography>
        <Stack spacing={2}>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Relevancy
            </Typography>
            <LinearProgress
              variant="determinate"
              value={evaluation.relevancy * 100}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Coherence
            </Typography>
            <LinearProgress
              variant="determinate"
              value={evaluation.coherence * 100}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Factual Accuracy
            </Typography>
            <LinearProgress
              variant="determinate"
              value={evaluation.factual_accuracy * 100}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Box>
        </Stack>
      </Paper>
    </Box>
  );
};

export default Results; 