import { createTheme } from '@mui/material/styles';

// Eclaire Trials brand colors
// Primary: Blue (#0074D9)
// Secondary: Orange (#FF9500)
// Accent: Purple (#7F4FBF)

const theme = createTheme({
  palette: {
    primary: {
      main: '#0074D9',
      light: '#4a9eed',
      dark: '#005bb0',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#FF9500',
      light: '#ffad40',
      dark: '#cc7700',
      contrastText: '#ffffff',
    },
    accent: {
      main: '#7F4FBF',
      light: '#9b73cf',
      dark: '#663d99',
      contrastText: '#ffffff',
    },
    background: {
      default: '#f5f7fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#333333',
      secondary: '#666666',
    },
    success: {
      main: '#28a745',
    },
    warning: {
      main: '#ffc107',
    },
    error: {
      main: '#dc3545',
    },
    info: {
      main: '#17a2b8',
    },
  },
  typography: {
    fontFamily: '"Segoe UI", "Roboto", "Helvetica Neue", sans-serif',
    h1: {
      fontWeight: 700,
      fontSize: '2.5rem',
    },
    h2: {
      fontWeight: 600,
      fontSize: '2rem',
    },
    h3: {
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    h4: {
      fontWeight: 600,
      fontSize: '1.25rem',
    },
    h5: {
      fontWeight: 600,
      fontSize: '1.1rem',
    },
    h6: {
      fontWeight: 600,
      fontSize: '1rem',
    },
    button: {
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        },
        containedPrimary: {
          '&:hover': {
            backgroundColor: '#005bb0',
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
          },
        },
        containedSecondary: {
          '&:hover': {
            backgroundColor: '#cc7700',
            boxShadow: '0 4px 8px rgba(0, 0, 0, 0.2)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          overflow: 'hidden',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
        },
      },
    },
  },
});

export default theme;
