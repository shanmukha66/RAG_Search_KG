import React from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';

function Navbar() {
  return (
    <AppBar position="static">
      <Toolbar>
        <Typography
          variant="h6"
          component={RouterLink}
          to="/"
          sx={{
            flexGrow: 1,
            textDecoration: 'none',
            color: 'inherit',
          }}
        >
          Multimodal RAG
        </Typography>
        <Box>
          <Button
            component={RouterLink}
            to="/upload"
            color="inherit"
            startIcon={<CloudUploadIcon />}
          >
            Upload
          </Button>
          <Button
            component={RouterLink}
            to="/search"
            color="inherit"
            startIcon={<SearchIcon />}
          >
            Search
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Navbar; 