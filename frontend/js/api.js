const API_BASE_URL = window.location.hostname === '127.0.0.1' || window.location.hostname === 'localhost'
    ? 'http://127.0.0.1:8000'
    : window.location.origin + '/api';

const api = {
    // ---------------- AUTH ----------------
    async loginWithLine() {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login/line`);
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Failed to initiate LINE Login");
            }
            if (data.url) {
                window.location.href = data.url;
            } else {
                throw new Error("No URL returned from server");
            }
        } catch (error) {
            console.error("LINE Login Error:", error);
            throw error;
        }
    },

    async loginWithEmail(email, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Login failed");
            
            if (data.token) {
                localStorage.setItem('access_token', data.token);
                window.location.href = 'index.html';
            }
            return data;
        } catch (error) {
            console.error("Email Login Error:", error);
            throw error;
        }
    },

    async register(userData) {
        try {
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(userData)
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Registration failed");
            
            if (data.token) {
                localStorage.setItem('access_token', data.token);
                window.location.href = 'index.html';
            }
            return data;
        } catch (error) {
            console.error("Registration Error:", error);
            throw error;
        }
    },

    logout() {
        localStorage.removeItem('access_token');
        window.location.href = 'login.html';
    },

    // ---------------- POSTS ----------------
    async getPosts(type = null, search = null, category = null) {
        try {
            let url = `${API_BASE_URL}/posts?`;
            if (type) url += `type=${type}&`;
            if (search) url += `search=${encodeURIComponent(search)}&`;
            if (category) url += `category=${encodeURIComponent(category)}&`;

            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error("Get Posts Error:", error);
            return { data: [] };
        }
    },

    async createPost(postData) {
        try {
            const token = localStorage.getItem('access_token');
            const response = await fetch(`${API_BASE_URL}/posts`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(postData)
            });
            if (response.status === 401) {
                localStorage.removeItem('access_token');
                alert("เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่อีกครั้ง");
                window.location.href = 'login.html';
                throw new Error("Session expired, redirecting to login...");
            }
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || "Error creating post");
            }
            return data;
        } catch (error) {
            console.error("Create Post Error:", error);
            throw error;
        }
    },

    async getRecommendations(postId) {
        try {
            const response = await fetch(`${API_BASE_URL}/posts/${postId}/recommendations`);
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Error fetching recommendations");
            return data;
        } catch (error) {
            console.error("Get Recommendations Error:", error);
            return { data: [] };
        }
    },

    async uploadImage(file) {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE_URL}/upload`, {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || "Error uploading image");
            return data.url;
        } catch (error) {
            console.error("Upload Image Error:", error);
            throw error;
        }
    }
};

// Utility to check auth state and handle OAuth callback
function checkAuth() {
    // Handle Supabase OAuth callback token from URL fragment
    const hash = window.location.hash;
    if (hash && hash.includes('access_token=')) {
        const params = new URLSearchParams(hash.substring(1));
        const accessToken = params.get('access_token');
        if (accessToken) {
            localStorage.setItem('access_token', accessToken);
            // Remove hash from URL without reloading
            window.history.replaceState(null, null, ' ');
        }
    }

    const token = localStorage.getItem('access_token');
    const hasToken = token && token !== 'undefined' && token !== 'null' && typeof token === 'string' && token.length > 10;
    const path = window.location.pathname;
    const isAuthPage = path.includes('login.html') || path.includes('register.html');

    // Enforce login logic
    if (!hasToken && !isAuthPage) {
        // Check if current page requires auth
        const protectedPages = ['create-post.html', 'profile.html', 'chat.html', 'chat-room.html'];
        const isProtected = protectedPages.some(page => path.endsWith(page) || path.includes('/' + page));

        if (isProtected) {
            console.log('Unauthorized access to protected page, redirecting to login...');
            window.location.href = 'login.html';
        }
    } else if (hasToken && isAuthPage) {
        window.location.href = 'index.html';
    }
}

document.addEventListener('DOMContentLoaded', checkAuth);
