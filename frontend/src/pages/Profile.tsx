// src/pages/Profile.tsx
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { format } from 'date-fns';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Grid,
  Divider
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../hooks/redux';
import { updateProfile, getProfile } from '../store/slices/authSlice'; // Assuming updateProfile handles password

// Validation schema for password update
// Note: The backend might require 'current_password'. Adjust schema and payload if needed.
const passwordUpdateSchema = z.object({
  // Uncomment if backend needs current password
  // currentPassword: z.string().min(1, 'Current password is required'),
  password: z.string().min(6, 'New password must be at least 6 characters'),
  confirmPassword: z.string().min(6, 'Confirm password must be at least 6 characters'),
}).refine(data => data.password === data.confirmPassword, {
  message: "New passwords don't match",
  path: ['confirmPassword'], // Apply error to confirmPassword field
});

type PasswordUpdateFormValues = z.infer<typeof passwordUpdateSchema>;

const Profile = () => {
  const dispatch = useAppDispatch();
  const { user, isLoading, error } = useAppSelector((state) => state.auth);

  // Fetch profile if user data isn't loaded (e.g., after refresh)
  useEffect(() => {
    if (!user) {
      dispatch(getProfile());
    }
  }, [dispatch, user]);

  const { register, handleSubmit, formState: { errors }, reset } = useForm<PasswordUpdateFormValues>({
    resolver: zodResolver(passwordUpdateSchema),
  });

  const onSubmitPassword = async (data: PasswordUpdateFormValues) => {



    //   // Adapt payload based on backend requirements
    // // Option 1: Only send new password (if backend derives user from token)
    // const payload = { password: data.password };
    // // Option 2: Send current and new password (adjust schema above too)
    // // const payload = { current_password: data.currentPassword, password: data.password };
    // Cast the payload to any or the correct expected type
    const payload = { password: data.password } as any; // or as Partial<User>
    
    const resultAction = await dispatch(updateProfile(payload));
    if (updateProfile.fulfilled.match(resultAction)) {
      reset();
    }
  };

  if (!user && isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!user) {
     return <Alert severity="error">Could not load user profile.</Alert>;
  }


  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        My Profile
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* User Information */}
        <Grid item xs={12} md={6}>
           <Paper sx={{ p: 3 }}>
               <Typography variant="h6" gutterBottom>User Information</Typography>
               <Divider sx={{ my: 2 }}/>
               <Box sx={{ mb: 2 }}>
                   <Typography variant="subtitle1" color="textSecondary">Email:</Typography>
                   <Typography variant="body1">{user.email}</Typography>
               </Box>
                <Box sx={{ mb: 2 }}>
                   <Typography variant="subtitle1" color="textSecondary">Joined:</Typography>
                   <Typography variant="body1">{format(new Date(user.created_at), 'PPP')}</Typography>
               </Box>
                {/* Add other user details if available in the 'user' object */}
           </Paper>
        </Grid>

        {/* Password Update */}
        <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>Change Password</Typography>
              <Divider sx={{ my: 2 }}/>
              <Box component="form" onSubmit={handleSubmit(onSubmitPassword)} noValidate>
                 {/* Uncomment if backend needs current password
                 <TextField
                    margin="normal"
                    required
                    fullWidth
                    label="Current Password"
                    type="password"
                    id="currentPassword"
                    {...register('currentPassword')}
                    error={!!errors.currentPassword}
                    helperText={errors.currentPassword?.message}
                    disabled={isLoading}
                  />
                  */}
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  label="New Password"
                  type="password"
                  id="password"
                  {...register('password')}
                  error={!!errors.password}
                  helperText={errors.password?.message}
                  disabled={isLoading}
                />
                <TextField
                  margin="normal"
                  required
                  fullWidth
                  label="Confirm New Password"
                  type="password"
                  id="confirmPassword"
                  {...register('confirmPassword')}
                  error={!!errors.confirmPassword}
                  helperText={errors.confirmPassword?.message}
                  disabled={isLoading}
                />
                <Button
                  type="submit"
                  variant="contained"
                  sx={{ mt: 3, mb: 2 }}
                  disabled={isLoading}
                >
                  {isLoading ? <CircularProgress size={24} /> : 'Update Password'}
                </Button>
              </Box>
            </Paper>
        </Grid>

      </Grid>
    </Box>
  );
};

export default Profile;