const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

const getHeaders = (token = null) => {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

const getErrorMessage = (detail, fallback) => {
  if (typeof detail === 'string' && detail.trim()) return detail;

  const issues = Array.isArray(detail) ? detail : [detail];
  const messages = issues.map((issue) => {
    if (typeof issue === 'string') return issue;
    if (!issue || typeof issue !== 'object') return '';

    const message = issue.msg || issue.message || issue.detail;
    if (typeof message !== 'string') return '';

    const location = Array.isArray(issue.loc) ? issue.loc[issue.loc.length - 1] : '';
    return location && location !== 'body' ? `${location}: ${message}` : message;
  }).filter(Boolean);

  return messages.length ? [...new Set(messages)].join(' ') : fallback;
};

const uploadForm = (path, formData, onProgress, method = 'POST') => new Promise((resolve, reject) => {
  const xhr = new XMLHttpRequest();
  xhr.open(method, `${API_BASE_URL}${path}`);
  xhr.withCredentials = true;
  xhr.setRequestHeader('Accept', 'application/json');
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
  };
  xhr.onerror = () => reject(new Error('OpenVibe could not reach the server. Check your connection and try again.'));
  xhr.onload = () => {
    let response;
    try { response = JSON.parse(xhr.responseText); }
    catch { response = {}; }
    if (xhr.status < 200 || xhr.status >= 300) {
      reject(new Error(getErrorMessage(response.detail, 'The upload could not be completed.')));
      return;
    }
    onProgress?.(100);
    resolve(response);
  };
  xhr.send(formData);
});

export const api = {
  // Auth
  register: async (username, email, password, termsAccepted, fullName = '') => {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ username, email, password, full_name: fullName, terms_accepted: termsAccepted })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(getErrorMessage(err.detail, 'Registration failed'));
    }
    return res.json();
  },

  listExplorePosts: async () => {
    const res = await fetch(`${API_BASE_URL}/posts/explore`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load Explore posts');
    return res.json();
  },

  login: async (email, password) => {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(getErrorMessage(err.detail, 'Login failed'));
    }
    return res.json();
  },

  getFollowRequests: async () => {
    const res = await fetch(`${API_BASE_URL}/follows/requests`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load follow requests');
    return res.json();
  },

  acceptFollowRequest: async (followerId) => {
    const res = await fetch(`${API_BASE_URL}/follows/requests/${encodeURIComponent(followerId)}/accept`, {
      method: 'POST', credentials: 'include', headers: getHeaders(),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not accept follow request'); }
    return res.json();
  },

  rejectFollowRequest: async (followerId) => {
    const res = await fetch(`${API_BASE_URL}/follows/requests/${encodeURIComponent(followerId)}/reject`, {
      method: 'POST', credentials: 'include', headers: getHeaders(),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not reject follow request'); }
    return res.json();
  },

  getMe: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      credentials: 'include',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error('Session expired');
    return res.json();
  },

  updateProfile: async ({ username, email, currentPassword, fullName, headline, location, about, skills, isPrivate }) => {
    const res = await fetch(`${API_BASE_URL}/auth/profile`, {
      method: 'PATCH', credentials: 'include', headers: getHeaders(),
      body: JSON.stringify({
        username, email, full_name: fullName, headline, location, about, skills,
        current_password: currentPassword, is_private: isPrivate,
      })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Profile update failed');
    }
    return res.json();
  },

  logout: async () => {
    const res = await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders()
    });
    if (!res.ok) throw new Error('Could not end the current session');
  },

  // Posts
  createPost: async (content) => {
    const res = await fetch(`${API_BASE_URL}/posts`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ content })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to create post');
    }
    return res.json();
  },

  createMediaPost: async (caption, files, onProgress) => {
    const formData = new FormData();
    formData.append('caption', caption);
    files.forEach((file) => formData.append('files', file));
    return uploadForm('/posts/media', formData, onProgress);
  },

  createEvent: async ({ title, description, eventDate, eventTime, location, coverImage }, onProgress) => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('description', description);
    formData.append('event_date', eventDate);
    formData.append('event_time', eventTime);
    formData.append('location', location);
    if (coverImage) formData.append('cover_image', coverImage);
    return uploadForm('/posts/events', formData, onProgress);
  },

  createArticle: async ({ title, content, coverImage }, onProgress) => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    if (coverImage) formData.append('cover_image', coverImage);
    return uploadForm('/posts/articles', formData, onProgress);
  },

  updateArticle: async (postId, { title, content, coverImage }, onProgress) => {
    const formData = new FormData();
    formData.append('title', title);
    formData.append('content', content);
    if (coverImage) formData.append('cover_image', coverImage);
    return uploadForm(`/posts/${encodeURIComponent(postId)}/article`, formData, onProgress, 'PUT');
  },

  deletePost: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}`, {
      method: 'DELETE', credentials: 'include', headers: getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(getErrorMessage(err.detail, 'Could not delete this post.'));
    }
    return res.json();
  },

  deletePostMedia: async (postId, filename) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}/media/${encodeURIComponent(filename)}`, {
      method: 'DELETE', credentials: 'include', headers: getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(getErrorMessage(err.detail, 'Could not remove this media.'));
    }
    return res.json();
  },

  mediaUrl: (path) => new URL(path, API_BASE_URL).href,

  listPosts: async (statusFilter = null, contentType = null) => {
    let url = `${API_BASE_URL}/posts`;
    if (statusFilter) url += `?status_filter=${statusFilter}`;
    if (contentType) url += `${statusFilter ? '&' : '?'}content_type=${encodeURIComponent(contentType)}`;
    const res = await fetch(url, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch posts');
    return res.json();
  },

  search: async (query) => {
    const res = await fetch(`${API_BASE_URL}/search?q=${encodeURIComponent(query)}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Search could not be completed');
    }
    return res.json();
  },

  searchUsers: async (query) => {
    const res = await fetch(`${API_BASE_URL}/users/search?q=${encodeURIComponent(query)}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'People search could not be completed');
    }
    return res.json();
  },

  getPublicProfile: async (userId) => {
    const res = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userId)}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load this profile');
    return res.json();
  },

  getPublicUserPosts: async (userId) => {
    const res = await fetch(`${API_BASE_URL}/users/${encodeURIComponent(userId)}/posts`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load posts for this profile');
    return res.json();
  },

  getMyPosts: async () => {
    const res = await fetch(`${API_BASE_URL}/posts/user/me`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch user posts');
    return res.json();
  },

  getUserDashboard: async () => {
    const res = await fetch(`${API_BASE_URL}/dashboard/me`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch dashboard');
    return res.json();
  },

  appealPost: async (postId, reason) => {
    const res = await fetch(`${API_BASE_URL}/posts/${postId}/appeal`, {
      method: 'POST', credentials: 'include', headers: getHeaders(),
      body: JSON.stringify({ reason })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Appeal failed');
    }
    return res.json();
  },

  likePost: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}/like`, { method: 'PUT', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not like this post');
    return res.json();
  },

  unlikePost: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}/like`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not remove your like');
    return res.json();
  },

  savePost: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}/save`, { method: 'PUT', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not save this post');
    return res.json();
  },

  unsavePost: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/posts/${encodeURIComponent(postId)}/save`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not remove this saved post');
    return res.json();
  },

  getSavedPosts: async () => {
    const res = await fetch(`${API_BASE_URL}/posts/saved/me`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load saved posts');
    return res.json();
  },

  // Comments
  createComment: async (postId, content, parentCommentId = null) => {
    const res = await fetch(`${API_BASE_URL}/comments`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ post_id: postId, content, parent_comment_id: parentCommentId })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to post comment');
    }
    return res.json();
  },

  listComments: async (postId) => {
    const res = await fetch(`${API_BASE_URL}/comments/post/${postId}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch comments');
    return res.json();
  },

  likeComment: async (commentId) => {
    const res = await fetch(`${API_BASE_URL}/comments/${encodeURIComponent(commentId)}/like`, { method: 'PUT', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not like this comment');
    return res.json();
  },

  unlikeComment: async (commentId) => {
    const res = await fetch(`${API_BASE_URL}/comments/${encodeURIComponent(commentId)}/like`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not remove your comment like');
    return res.json();
  },

  deleteComment: async (commentId) => {
    const res = await fetch(`${API_BASE_URL}/comments/${encodeURIComponent(commentId)}`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not delete this comment'); }
    return res.json();
  },

  getConnectionSuggestions: async () => {
    const res = await fetch(`${API_BASE_URL}/connections/suggestions`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load member suggestions');
    return res.json();
  },

  getConnectionRequests: async () => {
    const res = await fetch(`${API_BASE_URL}/connections/requests`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load invitations');
    return res.json();
  },

  getConnections: async () => {
    const res = await fetch(`${API_BASE_URL}/connections`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load your connections');
    return res.json();
  },

  requestConnection: async (targetUserId) => {
    const res = await fetch(`${API_BASE_URL}/connections/requests`, { method: 'POST', credentials: 'include', headers: getHeaders(), body: JSON.stringify({ target_user_id: targetUserId }) });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Connection request failed'); }
    return res.json();
  },

  acceptConnection: async (connectionId) => {
    const res = await fetch(`${API_BASE_URL}/connections/${encodeURIComponent(connectionId)}/accept`, { method: 'POST', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not accept invitation'); }
    return res.json();
  },

  rejectConnection: async (connectionId) => {
    const res = await fetch(`${API_BASE_URL}/connections/${encodeURIComponent(connectionId)}/reject`, { method: 'POST', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not decline invitation'); }
    return res.json();
  },

  removeConnection: async (targetUserId) => {
    const res = await fetch(`${API_BASE_URL}/connections/member/${encodeURIComponent(targetUserId)}`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not remove connection'); }
    return res.json();
  },

  followUser: async (userId) => {
    const res = await fetch(`${API_BASE_URL}/follows/${encodeURIComponent(userId)}`, { method: 'PUT', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not follow this member'); }
    return res.json();
  },

  unfollowUser: async (userId) => {
    const res = await fetch(`${API_BASE_URL}/follows/${encodeURIComponent(userId)}`, { method: 'DELETE', credentials: 'include', headers: getHeaders() });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not unfollow this member'); }
    return res.json();
  },

  getMyFollows: async () => {
    const res = await fetch(`${API_BASE_URL}/follows/me`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load follows');
    return res.json();
  },

  getNotifications: async () => {
    const res = await fetch(`${API_BASE_URL}/notifications`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load notifications');
    return res.json();
  },

  markNotificationRead: async (notificationId) => {
    const res = await fetch(`${API_BASE_URL}/notifications/${encodeURIComponent(notificationId)}/read`, { method: 'PATCH', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not update notification');
    return res.json();
  },

  markAllNotificationsRead: async () => {
    const res = await fetch(`${API_BASE_URL}/notifications/read-all`, { method: 'POST', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not update notifications');
    return res.json();
  },

  getConversations: async () => {
    const res = await fetch(`${API_BASE_URL}/messages/conversations`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load conversations');
    return res.json();
  },

  startConversation: async (participantId) => {
    const res = await fetch(`${API_BASE_URL}/messages/conversations`, { method: 'POST', credentials: 'include', headers: getHeaders(), body: JSON.stringify({ participant_id: participantId }) });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not start conversation'); }
    return res.json();
  },

  getConversation: async (conversationId) => {
    const res = await fetch(`${API_BASE_URL}/messages/conversations/${encodeURIComponent(conversationId)}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load this conversation');
    return res.json();
  },

  sendMessage: async (conversationId, content) => {
    const res = await fetch(`${API_BASE_URL}/messages/conversations/${encodeURIComponent(conversationId)}/messages`, { method: 'POST', credentials: 'include', headers: getHeaders(), body: JSON.stringify({ content }) });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Message could not be sent'); }
    return res.json();
  },

  markConversationRead: async (conversationId) => {
    const res = await fetch(`${API_BASE_URL}/messages/conversations/${encodeURIComponent(conversationId)}/read`, { method: 'PATCH', credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not update conversation');
    return res.json();
  },

  // Interactive Sandbox
  analyzeText: async (text) => {
    const res = await fetch(`${API_BASE_URL}/moderation/analyze`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ text, include_explanation: true })
    });
    if (!res.ok) throw new Error('Analysis failed');
    return res.json();
  },

  // Admin
  getReviewQueue: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/queue`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch review queue');
    return res.json();
  },

  reviewPost: async (postId, action, contentType = 'post', confirmAction = false) => {
    const res = await fetch(`${API_BASE_URL}/admin/review/${postId}?content_type=${encodeURIComponent(contentType)}`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ action, confirm_action: confirmAction })
    });
    if (!res.ok) throw new Error('Failed to update review status');
    return res.json();
  },

  getAuditLogs: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/audit-logs`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch audit logs');
    return res.json();
  },

  getAnalytics: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/analytics`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch analytics');
    return res.json();
  },

  generateReport: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/report`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to generate report');
    return res.json();
  },

  getAdminContent: async (contentId, contentType = 'post') => {
    const res = await fetch(`${API_BASE_URL}/admin/content/${contentId}?content_type=${encodeURIComponent(contentType)}`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to load content for review');
    return res.json();
  },

  getModerationHistory: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/moderation-history`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch moderation history');
    return res.json();
  },

  getAdminUsers: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/users`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch users');
    return res.json();
  },

  updateAdminUserAccess: async (userId, updates) => {
    const res = await fetch(`${API_BASE_URL}/admin/users/${encodeURIComponent(userId)}`, {
      method: 'PATCH', credentials: 'include', headers: getHeaders(), body: JSON.stringify(updates),
    });
    if (!res.ok) { const err = await res.json(); throw new Error(err.detail || 'Could not update this account'); }
    return res.json();
  },

  getAdminPrivacyRequests: async () => {
    const res = await fetch(`${API_BASE_URL}/admin/privacy-requests`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch privacy requests');
    return res.json();
  },

  updateAdminPrivacyRequest: async (requestId, status, response) => {
    const res = await fetch(`${API_BASE_URL}/admin/privacy-requests/${encodeURIComponent(requestId)}`, {
      method: 'PATCH', credentials: 'include', headers: getHeaders(),
      body: JSON.stringify({ status, response })
    });
    if (!res.ok) throw new Error('Failed to update privacy request');
    return res.json();
  },

  // Privacy
  getPrivacyContact: async () => {
    const res = await fetch(`${API_BASE_URL}/privacy/contact`);
    if (!res.ok) throw new Error('Could not load operator contact information');
    return res.json();
  },

  saveConsent: async (analyticsCookies) => {
    const res = await fetch(`${API_BASE_URL}/privacy/consent`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ analytics_cookies: analyticsCookies, policy_version: '1.0' })
    });
    if (!res.ok) throw new Error('Could not save consent preference');
    return res.json();
  },

  createPrivacyRequest: async (requestType, description) => {
    const res = await fetch(`${API_BASE_URL}/privacy/requests`, {
      method: 'POST', credentials: 'include', headers: getHeaders(),
      body: JSON.stringify({ request_type: requestType, description })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Could not submit the privacy request');
    }
    return res.json();
  },

  getMyPrivacyRequests: async () => {
    const res = await fetch(`${API_BASE_URL}/privacy/requests/me`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Could not load your privacy requests');
    return res.json();
  },

  exportData: async () => {
    const res = await fetch(`${API_BASE_URL}/privacy/export-data`, { credentials: 'include', headers: getHeaders() });
    if (!res.ok) throw new Error('Data export failed');
    return res.json();
  },

  deleteAccount: async () => {
    const res = await fetch(`${API_BASE_URL}/privacy/delete-account`, {
      method: 'POST',
      credentials: 'include',
      headers: getHeaders(),
      body: JSON.stringify({ confirm_deletion: true })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Account deletion failed');
    }
    return res.json();
  }
};
