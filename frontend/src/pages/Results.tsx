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
  CircularProgress,
  Alert,
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

interface LocationState {
  query: string;
  queryType: string;
  results: {
    answer: string;
    confidence: number;
    sources: Array<{
      title: string;
      type: string;
      relevance: number;
      content?: string;
    }>;
    cross_references: Array<{
      text: string;
      source: string;
      confidence: number;
    }>;
    evaluation: {
      relevance: number;
      factuality: number;
      coherence: number;
    };
  };
}

const Results: React.FC = () => {
  const location = useLocation();
  const { query, queryType, results } = (location.state as LocationState) || {};

  if (!query || !results) {
    return <Navigate to="/" replace />;
  }

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'text':
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

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.6) return 'warning';
    return 'error';
  };

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', mt: 4 }}>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="subtitle1" color="textSecondary">
          Query
        </Typography>
        <Typography variant="h6" gutterBottom>
          {query}
        </Typography>
        <Chip label={queryType} color="primary" size="small" sx={{ mt: 1 }} />
      </Paper>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="subtitle1" color="textSecondary" gutterBottom>
            Answer
          </Typography>
          <Typography variant="body1" paragraph>
            {results.answer}
          </Typography>

          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Confidence Score
              </Typography>
              <Stack direction="row" spacing={1} alignItems="center">
                <Box sx={{ flexGrow: 1 }}>
                  <LinearProgress
                    variant="determinate"
                    value={results.confidence * 100}
                    color={getConfidenceColor(results.confidence)}
                  />
                </Box>
                <Typography variant="body2">
                  {(results.confidence * 100).toFixed(1)}%
                </Typography>
              </Stack>
            </Box>

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Evaluation Metrics
              </Typography>
              <Stack spacing={1}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" sx={{ minWidth: 100 }}>
                    Relevance:
                  </Typography>
                  <Box sx={{ flexGrow: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={results.evaluation.relevance * 100}
                      color={getConfidenceColor(results.evaluation.relevance)}
                    />
                  </Box>
                  <Typography variant="body2">
                    {(results.evaluation.relevance * 100).toFixed(1)}%
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" sx={{ minWidth: 100 }}>
                    Factuality:
                  </Typography>
                  <Box sx={{ flexGrow: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={results.evaluation.factuality * 100}
                      color={getConfidenceColor(results.evaluation.factuality)}
                    />
                  </Box>
                  <Typography variant="body2">
                    {(results.evaluation.factuality * 100).toFixed(1)}%
                  </Typography>
                </Stack>

                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" sx={{ minWidth: 100 }}>
                    Coherence:
                  </Typography>
                  <Box sx={{ flexGrow: 1 }}>
                    <LinearProgress
                      variant="determinate"
                      value={results.evaluation.coherence * 100}
                      color={getConfidenceColor(results.evaluation.coherence)}
                    />
                  </Box>
                  <Typography variant="body2">
                    {(results.evaluation.coherence * 100).toFixed(1)}%
                  </Typography>
                </Stack>
              </Stack>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6" gutterBottom>
        Sources
      </Typography>
      <List>
        {results.sources.map((source, index) => (
          <React.Fragment key={index}>
            {index > 0 && <Divider />}
            <ListItem>
              <ListItemIcon>{getSourceIcon(source.type)}</ListItemIcon>
              <ListItemText
                primary={source.title}
                secondary={
                  <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                    <Chip
                      label={source.type}
                      size="small"
                      variant="outlined"
                    />
                    <Chip
                      label={`${(source.relevance * 100).toFixed(1)}% relevant`}
                      size="small"
                      color={getConfidenceColor(source.relevance)}
                    />
                  </Stack>
                }
              />
            </ListItem>
            {source.content && (
              <Box sx={{ pl: 9, pr: 2, pb: 2 }}>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    bgcolor: 'action.hover',
                    p: 1,
                    borderRadius: 1,
                    maxHeight: 100,
                    overflow: 'auto',
                  }}
                >
                  {source.content}
                </Typography>
              </Box>
            )}
          </React.Fragment>
        ))}
      </List>

      {results.cross_references.length > 0 && (
        <>
          <Typography variant="h6" gutterBottom sx={{ mt: 4 }}>
            Cross References
          </Typography>
          <List>
            {results.cross_references.map((ref, index) => (
              <React.Fragment key={index}>
                {index > 0 && <Divider />}
                <ListItem>
                  <ListItemText
                    primary={ref.text}
                    secondary={
                      <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                        <Chip
                          label={`Source: ${ref.source}`}
                          size="small"
                          variant="outlined"
                        />
                        <Chip
                          label={`${(ref.confidence * 100).toFixed(1)}% confidence`}
                          size="small"
                          color={getConfidenceColor(ref.confidence)}
                        />
                      </Stack>
                    }
                  />
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        </>
      )}
    </Box>
  );
};

export default Results; 