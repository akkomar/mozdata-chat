const gcipCloudFunctions = require('gcip-cloud-functions');

// Create an Auth client for handling blocking function events
const authClient = new gcipCloudFunctions.Auth();

/**
 * Blocking function that runs before a user signs in.
 * Rejects sign-in attempts from non-Mozilla email addresses.
 */
exports.beforeSignIn = authClient.functions().beforeSignInHandler((user, context) => {
  // Check if user has an email and it ends with @mozilla.com
  if (!user.email || !user.email.endsWith('@mozilla.com')) {
    throw new gcipCloudFunctions.https.HttpsError(
      'invalid-argument',
      'Access restricted: Only Mozilla employees (@mozilla.com) can access this application.'
    );
  }

  // Allow Mozilla users to proceed with sign-in
  console.log(`Sign-in allowed for Mozilla user: ${user.email}`);
});

/**
 * Blocking function that runs before a new user account is created.
 * Prevents creation of accounts with non-Mozilla email addresses.
 */
exports.beforeCreate = authClient.functions().beforeCreateHandler((user, context) => {
  // Check if user has an email and it ends with @mozilla.com
  if (!user.email || !user.email.endsWith('@mozilla.com')) {
    throw new gcipCloudFunctions.https.HttpsError(
      'invalid-argument',
      'Account creation restricted: Only Mozilla employees (@mozilla.com) can register for this application.'
    );
  }

  // Allow Mozilla users to create accounts
  console.log(`Account creation allowed for Mozilla user: ${user.email}`);
});
