// Global App Logic for Dynamic Data Rendering

// Dynamically inject SweetAlert2 if not present
if (typeof window.Swal === 'undefined') {
    const script = document.createElement('script');
    script.src = "https://cdn.jsdelivr.net/npm/sweetalert2@11";
    document.head.appendChild(script);
}

window.ayayaAlert = function(msg, type = 'warning', callback = null) {
    if (window.Swal) {
        Swal.fire({
            text: msg,
            icon: type,
            confirmButtonColor: '#ea580c',
            confirmButtonText: 'ตกลง'
        }).then(() => {
            if (callback) callback();
        });
    } else {
        alert(msg);
        if (callback) callback();
    }
};

window.ayayaConfirm = async function(msg) {
    if (window.Swal) {
        const result = await Swal.fire({
            text: msg,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#ea580c',
            cancelButtonColor: '#6b7280',
            confirmButtonText: 'ตกลง',
            cancelButtonText: 'ยกเลิก'
        });
        return result.isConfirmed;
    } else {
        return confirm(msg);
    }
};

async function loadHomePosts(type = null) {
    const container = document.getElementById('post-container');
    if (!container) return;

    // Update Filter Buttons UI
    const filters = {
        'all': document.getElementById('filter-all'),
        'lost': document.getElementById('filter-lost'),
        'found': document.getElementById('filter-found')
    };

    Object.keys(filters).forEach(key => {
        const btn = filters[key];
        if (!btn) return;
        if ((key === 'all' && !type) || key === type) {
            btn.classList.remove('bg-white', 'text-gray-600', 'border-gray-200');
            btn.classList.add('bg-gray-900', 'text-white', 'shadow-md');
        } else {
            btn.classList.remove('bg-gray-900', 'text-white', 'shadow-md');
            btn.classList.add('bg-white', 'text-gray-600', 'border-gray-200');
        }
    });

    try {
        const token = localStorage.getItem('access_token');
        let isAdmin = false;
        if (token) {
            try {
                const meResp = await fetch(`${API_BASE_URL}/users/me`, { headers: { 'Authorization': `Bearer ${token}` } });
                const user = await meResp.json();
                isAdmin = user && (user.is_admin || user.is_super_admin);
            } catch (e) { }
        }

        const response = await api.getPosts(type);
        const posts = (response.data || []).slice(0, 2);

        container.innerHTML = ''; // Clear hardcoded content

        if (posts.length === 0) {
            container.innerHTML = `<div class="col-span-full text-center py-20 text-gray-500 font-medium">ยังไม่มีประกาศ${type === 'lost' ? 'ตามหาของ' : (type === 'found' ? 'เจอของ' : '')}ในขณะนี้</div>`;
            return;
        }

        posts.forEach(post => {
            const isLost = post.type === 'lost';
            const badgeColor = isLost ? 'bg-red-500' : 'bg-green-500';
            const badgeText = isLost ? 'ตามหาของหาย' : 'เจอของ';

            const status = post.status || 'published';
            let statusText = 'ประกาศแล้ว';
            let statusColor = 'bg-blue-500';

            if (status === 'pending') {
                statusText = 'รอประกาศ';
                statusColor = 'bg-amber-500';
            } else if (status === 'claimed') {
                statusText = isLost ? 'ได้รับของแล้ว' : 'ส่งคืนเจ้าของแล้ว';
                statusColor = 'bg-gray-500';
            }
            if (post.status_by_name && status !== 'pending') {
                statusText += ` (โดย ${post.status_by_name})`;
            }

            let adminBar = '';
            if (isAdmin) {
                adminBar = `
                <div class="bg-slate-50 border-t border-slate-100 p-2 flex justify-between items-center">
                    <span class="text-[10px] font-bold text-slate-500"><i data-lucide="shield-check" class="w-3 h-3 inline"></i> แอดมิน: เปลี่ยนสถานะ</span>
                    <select onchange="updatePostStatus(event, '${post.id}', this.value)" class="px-2 py-1 bg-white text-[10px] font-bold text-primary-600 rounded-lg border border-slate-200 shadow-sm outline-none cursor-pointer">
                        <option value="pending" ${status === 'pending' ? 'selected' : ''}>รอประกาศ</option>
                        <option value="published" ${status === 'published' ? 'selected' : ''}>ประกาศแล้ว</option>
                        <option value="claimed" ${status === 'claimed' ? 'selected' : ''}>เจ้าของมารับแล้ว</option>
                    </select>
                </div>`;
            }

            const statusDisplay = `<div class="absolute bottom-2 left-2 px-2 py-0.5 ${statusColor} text-[8px] font-extrabold text-white rounded-full uppercase shadow-sm">${statusText}</div>`;

            const card = `
            <div class="bg-white rounded-2xl shadow-sm hover:shadow-md border border-gray-100 overflow-hidden transition-all flex flex-col">
                <a href="post-detail.html?id=${post.id}" class="group relative flex h-32">
                    <div class="w-32 h-full bg-gray-100 relative shrink-0">
                        <img src="${(post.image_url && post.image_url.split(',')[0]) || 'https://via.placeholder.com/200?text=No+Image'}" class="w-full h-full object-cover">
                        <div class="absolute top-2 left-2 px-2 py-0.5 ${badgeColor} text-[8px] font-extrabold text-white rounded-full uppercase">${badgeText}</div>
                        ${statusDisplay}
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-center min-w-0">
                        <div class="flex justify-between items-start">
                            <h4 class="font-bold text-gray-900 line-clamp-1 mb-1 group-hover:text-primary-600 transition-colors">${post.title}</h4>
                        </div>
                        <p class="text-xs text-gray-500 line-clamp-1 mb-2 leading-tight">${post.description}</p>
                        <div class="flex items-center gap-2 text-[10px] text-gray-400 font-medium mt-1">
                            <span class="flex items-center gap-1 bg-gray-50 px-1.5 py-0.5 rounded-md"><i data-lucide="user" class="w-3 h-3 text-slate-400"></i> ${post.author_name || '-'}</span>
                            <span class="flex items-center gap-1 bg-gray-50 px-1.5 py-0.5 rounded-md"><i data-lucide="calendar" class="w-3 h-3"></i> ${post.lost_found_date || 'ไม่ระบุวันที่'}</span>
                            <span class="flex items-center gap-1"><i data-lucide="map-pin" class="w-3 h-3 text-primary-400"></i> ${post.location}</span>
                        </div>
                    </div>
                </a>
                ${adminBar}
            </div>`;
            container.innerHTML += card;
        });
        lucide.createIcons();
    } catch (err) {
        container.innerHTML = `<div class="col-span-full text-center py-10 text-red-500 font-medium">ไม่สามารถโหลดข้อมูลได้</div>`;
    }
}


async function loadProfile() {
    const profileName = document.getElementById('profile-name');
    const profileEmail = document.getElementById('profile-email');
    if (!profileName) return;

    const token = localStorage.getItem('access_token');
    const hasToken = token && token !== 'undefined' && token !== 'null' && typeof token === 'string' && token.length > 10;

    if (!hasToken) {
        if (profileName) profileName.textContent = 'กรุณาเข้าสู่ระบบ';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            if (response.status === 401) {
                localStorage.removeItem('access_token');
                window.location.href = 'login.html';
                return;
            }
            throw new Error("Unauthorized");
        }

        const user = await response.json();

        if (user && (user.email || user.id)) {
            profileName.textContent = user.full_name || 'ผู้ใช้งาน';
            if (profileEmail) profileEmail.textContent = user.email || 'LINE User';

            if (user.avatar_url) {
                const img = document.getElementById('profile-img');
                if (img) img.src = user.avatar_url;
            }

            // Load user posts
            try {
                const postsResp = await fetch(`${API_BASE_URL}/posts?user_id=${user.id}`);
                const postsData = await postsResp.json();
                const posts = postsData.data || [];

                // Calculate Stats
                const lostCount = posts.filter(p => p.type === 'lost').length;
                const foundCount = posts.filter(p => p.type === 'found').length;

                const statLost = document.getElementById('stat-lost');
                const statFound = document.getElementById('stat-found');
                if (statLost) statLost.textContent = lostCount;
                if (statFound) statFound.textContent = foundCount;

                // Render My Posts
                const postsContainer = document.getElementById('my-posts-container');
                if (postsContainer) {
                    postsContainer.innerHTML = '';
                    if (posts.length === 0) {
                        postsContainer.innerHTML = '<div class="text-center py-4 text-gray-500 text-sm font-medium">ยังไม่มีประกาศของคุณ</div>';
                    } else {
                        posts.forEach(post => {
                            const isLost = post.type === 'lost';
                            const badgeColor = isLost ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700';
                            const badgeText = isLost ? 'ตามหาของ' : 'เจอของ';

                            postsContainer.innerHTML += `
                            <a href="post-detail.html?id=${post.id}" class="flex items-center justify-between bg-white p-4 rounded-3xl shadow-sm border border-gray-100 hover:shadow-md transition">
                                <div class="flex items-center gap-4">
                                    <img src="${(post.image_url && post.image_url.split(',')[0]) || 'https://via.placeholder.com/100?text=No+Image'}" class="w-16 h-16 rounded-2xl object-cover shrink-0">
                                    <div>
                                        <h4 class="font-bold text-gray-900 line-clamp-1">${post.title}</h4>
                                        <span class="inline-block mt-1 px-2 py-0.5 ${badgeColor} text-[10px] font-extrabold rounded-md uppercase">${badgeText}</span>
                                    </div>
                                </div>
                                <button class="p-2 text-gray-400 hover:text-gray-900 bg-gray-50 rounded-full">
                                    <i data-lucide="chevron-right" class="w-5 h-5"></i>
                                </button>
                            </a>`;
                        });
                        lucide.createIcons();
                    }
                }
            } catch (err) {
                console.error("Load Profile Posts Error:", err);
            }
        } else {
            profileName.textContent = 'กรุณาเข้าสู่ระบบ';
            if (profileEmail) profileEmail.textContent = '';
        }
    } catch (err) {
        console.error("Load Profile Error:", err);
        profileName.textContent = 'กรุณาเข้าสู่ระบบ';
        if (profileEmail) profileEmail.textContent = '';
    }
}

async function loadPostDetail() {
    const detailContainer = document.getElementById('post-detail-container');
    if (!detailContainer) return;

    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get('id');

    if (!postId) {
        detailContainer.innerHTML = '<div class="text-center py-20 text-red-500 font-bold text-xl">ไม่พบประกาศนี้</div>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/posts/${postId}`);
        const result = await response.json();
        const post = result.data;

        if (!post) throw new Error("No post data");

        // Update title & content
        document.getElementById('detail-title').textContent = post.title || 'ไม่มีหัวข้อ';
        document.getElementById('detail-desc').textContent = post.description || '-';
        document.getElementById('detail-loc').textContent = post.location || '-';
        document.getElementById('detail-date').textContent = post.lost_found_date || '-';
        document.getElementById('detail-cat').textContent = `หมวดหมู่: ${post.category || '-'}`;

        // Update image/gallery
        const detailImg = document.getElementById('detail-img');
        const galleryContainer = document.getElementById('detail-gallery');
        if (post.image_url) {
            const images = post.image_url.split(',');
            if (detailImg) {
                detailImg.src = images[0];
                detailImg.onclick = () => window.open(images[0], '_blank');
            }

            if (galleryContainer && images.length > 1) {
                galleryContainer.classList.remove('hidden');
                galleryContainer.innerHTML = '';
                images.forEach((url, i) => {
                    const imgDiv = document.createElement('div');
                    imgDiv.className = `cursor-pointer rounded-xl overflow-hidden border-2 transition-all ${i === 0 ? 'border-primary-500 shadow-md' : 'border-transparent opacity-60 hover:opacity-100'}`;
                    imgDiv.innerHTML = `<img src="${url}" class="w-full aspect-square object-cover">`;
                    imgDiv.onclick = () => {
                        if (detailImg) detailImg.src = url;
                        // Update border style for active thumbnail
                        Array.from(galleryContainer.children).forEach(child => child.classList.add('border-transparent', 'opacity-60'));
                        Array.from(galleryContainer.children).forEach(child => child.classList.remove('border-primary-500', 'shadow-md'));
                        imgDiv.classList.remove('border-transparent', 'opacity-60');
                        imgDiv.classList.add('border-primary-500', 'shadow-md');
                    };
                    galleryContainer.appendChild(imgDiv);
                });
            }
        } else if (detailImg) {
            detailImg.src = 'https://via.placeholder.com/1200x800?text=ไม่มีรูปภาพ';
        }

        // Update type badge
        const isLost = post.type === 'lost';
        const badge = document.getElementById('detail-type-badge');
        const badgeText = document.getElementById('detail-type-text');
        if (badge) badge.className = `w-2.5 h-2.5 rounded-full animate-pulse ${isLost ? 'bg-red-500' : 'bg-green-500'}`;
        if (badgeText) badgeText.textContent = isLost ? 'ตามหาของหาย' : 'เจอของ';

        // Update status badge
        const status = post.status || 'published';
        const statusBadge = document.getElementById('detail-status-badge');
        const statusText = document.getElementById('detail-status-text');
        let sText = 'ประกาศแล้ว';
        let sColor = 'bg-blue-500';

        if (status === 'pending') {
            sText = 'รอประกาศ';
            sColor = 'bg-amber-500';
        } else if (status === 'claimed') {
            sText = isLost ? 'ได้รับของแล้ว' : 'ส่งคืนเจ้าของแล้ว';
            sColor = 'bg-gray-500';
        }
        if (post.status_by_name && status !== 'pending') {
            sText += ` (โดย ${post.status_by_name})`;
        }

        if (statusBadge) statusBadge.className = `w-2.5 h-2.5 rounded-full animate-pulse ${sColor}`;
        if (statusText) statusText.textContent = sText;

        // Check ownership to show management tools
        const token = localStorage.getItem('access_token');
        if (token && token !== 'null') {
            try {
                const meResp = await fetch(`${API_BASE_URL}/users/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (meResp.ok) {
                    const me = await meResp.json();
                    if (me.id === post.user_id) {
                        const manageSection = document.getElementById('owner-manage-section');
                        if (manageSection) manageSection.classList.remove('hidden');
                        
                        const statusBtn = document.getElementById('owner-status-btn');
                        if (statusBtn) {
                            statusBtn.textContent = `ตั้งเป็น: เสร็จสิ้น (${isLost ? 'ได้รับของแล้ว' : 'ส่งคืนเจ้าของแล้ว'})`;
                        }
                    }
                }
            } catch (e) { console.warn("Check ownership error", e); }
        }

        // Load poster info
        if (post.user_id) {
            try {
                const userResp = await fetch(`${API_BASE_URL}/users/${post.user_id}`);
                if (userResp.ok) {
                    const userData = await userResp.json();
                    const userName = userData.full_name || 'ผู้ใช้งาน';
                    const userAvatar = userData.avatar_url || `https://ui-avatars.com/api/?name=${encodeURIComponent(userName)}&background=ffedd5&color=ea580c`;

                    const userImg = document.getElementById('detail-user-img');
                    const userNameEl = document.getElementById('detail-user-name');
                    const profileLink = document.getElementById('detail-profile-link');

                    if (userImg) userImg.src = userAvatar;
                    if (userNameEl) userNameEl.textContent = userName;
                    if (profileLink) profileLink.href = `public-profile.html?id=${post.user_id}`;

                    // Add LINE button & ID display if user has LINE social ID
                    const lineBtn = document.getElementById('detail-line-btn');
                    const lineIdBox = document.getElementById('detail-line-id-box');
                    const lineIdText = document.getElementById('detail-line-id-text');
                    if (userData.line_social_id) {
                        if (lineIdBox) { lineIdBox.classList.remove('hidden'); }
                        if (lineIdText) { lineIdText.textContent = `@${userData.line_social_id}`; }
                        if (lineBtn) {
                            lineBtn.href = `https://line.me/ti/p/~${userData.line_social_id}`;
                            lineBtn.classList.remove('hidden');
                        }
                    }
                }
            } catch (e) {
                console.warn("Could not load poster info", e);
            }
        }

        // Load matching recommendations
        try {
            const recsResult = await api.getRecommendations(postId);
            const recommendations = recsResult.data || [];
            const recsList = document.getElementById('detail-recommendations-list');
            if (recsList) {
                recsList.innerHTML = '';
                if (recommendations.length === 0) {
                    recsList.innerHTML = `
                        <div class="col-span-full text-center py-10 bg-gray-50 rounded-2xl border border-dashed border-gray-200 text-gray-500 font-medium">
                            <i data-lucide="search-code" class="w-12 h-12 mx-auto text-gray-400 mb-3 block"></i>
                            ไม่พบเบาะแสอื่นในระบบที่ใกล้เคียงกับประกาศนี้ในขณะนี้
                        </div>
                    `;
                } else {
                    recommendations.forEach(item => {
                        const images = item.image_url ? item.image_url.split(',') : [];
                        const primaryImg = images.length > 0 && images[0] ? images[0] : 'https://via.placeholder.com/400x300?text=No+Image';
                        
                        let reasons = [];
                        if (item.match_breakdown) {
                            if (item.match_breakdown.category && item.match_breakdown.category.score > 0) reasons.push("หมวดหมู่ตรงกัน");
                            if (item.match_breakdown.location && item.match_breakdown.location.score >= 10) reasons.push("สถานที่ใกล้เคียง");
                            if (item.match_breakdown.date && item.match_breakdown.date.score >= 6) reasons.push("ช่วงเวลาใกล้เคียงกัน");
                            if (item.match_breakdown.title && item.match_breakdown.title.score >= 10) reasons.push("หัวข้อคล้ายกัน");
                        }
                        const reasonsText = reasons.join(', ') || 'ข้อมูลสอดคล้องกัน';
                        
                        function getMatchBadgeColor(score) {
                            if (score >= 80) return 'bg-green-50 text-green-700 border-green-200';
                            if (score >= 50) return 'bg-amber-50 text-amber-700 border-amber-200';
                            return 'bg-gray-50 text-gray-700 border-gray-200';
                        }
                        
                        const div = document.createElement('div');
                        div.className = "bg-white border border-gray-200 rounded-2xl p-4 flex gap-4 hover:shadow-md transition-shadow relative overflow-hidden group";
                        div.innerHTML = `
                            <!-- Image -->
                            <div class="w-24 h-24 rounded-xl overflow-hidden bg-gray-50 flex-shrink-0 border border-gray-100">
                                <img src="${primaryImg}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300">
                            </div>

                            <!-- Details -->
                            <div class="flex-1 flex flex-col justify-between min-w-0">
                                <div>
                                    <div class="flex items-center justify-between gap-2 mb-1">
                                        <span class="inline-block text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                                            ${item.type === 'lost' ? 'ตามหาของหาย' : 'เจอของคนอื่น'}
                                        </span>
                                        <span class="px-2 py-0.5 text-xs font-bold rounded-full border ${getMatchBadgeColor(item.match_score)}">
                                            โอกาสตรงกัน ${item.match_score}%
                                        </span>
                                    </div>
                                    <h4 class="font-bold text-gray-900 truncate text-sm mb-1">${item.title}</h4>
                                    
                                    <!-- Location and Date -->
                                    <div class="space-y-0.5 text-xs text-gray-500 font-medium">
                                        <div class="flex items-center gap-1">
                                            <i data-lucide="map-pin" class="w-3.5 h-3.5 text-gray-400"></i>
                                            <span class="truncate text-gray-600">${item.location || '-'}</span>
                                        </div>
                                        <div class="flex items-center gap-1">
                                            <i data-lucide="calendar" class="w-3.5 h-3.5 text-gray-400"></i>
                                            <span class="text-gray-600">${item.lost_found_date ? item.lost_found_date.split('T')[0] : 'ไม่ระบุ'}</span>
                                        </div>
                                    </div>
                                </div>

                                <div class="mt-2 flex justify-between items-center pt-1 border-t border-gray-50">
                                    <span class="text-[10px] text-gray-400">โดย: ${item.author_name || 'ผู้ใช้งาน'}</span>
                                    <a href="post-detail.html?id=${item.id}" class="text-xs font-bold text-primary-600 hover:text-primary-700 flex items-center gap-0.5">
                                        ดูรายละเอียด <i data-lucide="external-link" class="w-3 h-3"></i>
                                    </a>
                                </div>
                            </div>
                        `;
                        recsList.appendChild(div);
                    });
                }
                lucide.createIcons();
            }
        } catch (e) {
            console.error("Error displaying recommendations on detail page", e);
            const recsList = document.getElementById('detail-recommendations-list');
            if (recsList) {
                recsList.innerHTML = `
                    <div class="col-span-full text-center py-6 text-red-500 text-sm font-medium">
                        ไม่สามารถโหลดข้อมูลเบาะแสจับคู่ในขณะนี้ได้
                    </div>
                `;
            }
        }

    } catch (err) {
        detailContainer.innerHTML = '<div class="text-center py-20 text-red-500 font-bold text-xl">ไม่พบประกาศนี้หรือเกิดข้อผิดพลาด</div>';
    }
}

async function ownerUpdateStatus(newStatus) {
    const urlParams = new URLSearchParams(window.location.search);
    const postId = urlParams.get('id');
    if (!postId) return;

    const token = localStorage.getItem('access_token');
    if (!token || token === 'null') {
        window.ayayaAlert('กรุณาเข้าสู่ระบบก่อนครับ', 'warning');
        return;
    }

    // ถ้าเลือก "เสร็จสิ้น" ให้กรอกเหตุผลก่อน
    let reason = '';

    if (newStatus === 'claimed') {
        reason = window.prompt('เสร็จสิ้นเพราะอะไร?');

        // กด Cancel
        if (reason === null) {
            return;
        }

        reason = reason.trim();

        if (!reason) {
            window.ayayaAlert('กรุณาระบุเหตุผลก่อนครับ', 'warning');
            return;
        }
    }

    const statusText = 
        newStatus === 'pending'
        ? 'รอประกาศ'
        : (newStatus === 'claimed' ? 'เสร็จสิ้น' : 'ประกาศแล้ว');

    try {
        const response = await fetch(`${API_URL}/admin/posts/${postId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                status: newStatus,
                completion_reason: reason || null
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'อัปเดตสถานะไม่สำเร็จ');
        }

        window.ayayaAlert(`เปลี่ยนสถานะเป็น "${statusText}" เรียบร้อยแล้ว`, 'success');
        
        // โหลดข้อมูลหน้าใหม่เพื่ออัปเดตสถานะล่าสุด
        if (typeof loadPostDetail === 'function') {
            loadPostDetail();
        } else {
            location.reload();
        }

    } catch (err) {
        console.error(err);
        window.ayayaAlert(err.message || 'เกิดข้อผิดพลาดในการเปลี่ยนสถานะ', 'error');
    }
}

// Search Page State
let currentSearchFilters = {
    type: null,
    category: null
};

async function updateSearchFilter(newFilters) {
    currentSearchFilters = { ...currentSearchFilters, ...newFilters };
    loadSearch(currentSearchFilters.type, currentSearchFilters.category);
}

async function loadSearch(type = null, category = null) {
    const container = document.getElementById('post-container');
    const searchInput = document.getElementById('search-input');
    if (!container) return;

    const query = searchInput ? searchInput.value : '';

    // Sync internal state if called from DOMContentLoaded or type buttons
    if (type !== undefined && type !== currentSearchFilters.type) currentSearchFilters.type = type;
    if (category !== undefined && category !== currentSearchFilters.category) currentSearchFilters.category = category;

    // Update Type Buttons UI
    const typeFilters = {
        'all': document.getElementById('filter-all'),
        'lost': document.getElementById('filter-lost'),
        'found': document.getElementById('filter-found')
    };

    Object.keys(typeFilters).forEach(key => {
        const btn = typeFilters[key];
        if (!btn) return;
        if ((key === 'all' && !currentSearchFilters.type) || key === currentSearchFilters.type) {
            btn.classList.remove('bg-white', 'text-gray-600', 'border-gray-100');
            btn.classList.add('bg-gray-900', 'text-white', 'shadow-md');
        } else {
            btn.classList.remove('bg-gray-900', 'text-white', 'shadow-md');
            btn.classList.add('bg-white', 'text-gray-600', 'border-gray-100');
        }
    });

    // Update Category Buttons UI
    const catButtons = {
        'all': document.getElementById('cat-all'),
        'อิเล็กทรอนิกส์': document.getElementById('cat-electronics'),
        'กระเป๋า': document.getElementById('cat-wallet'),
        'เอกสาร': document.getElementById('cat-doc'),
        'กุญแจ': document.getElementById('cat-key'),
        'สัตว์เลี้ยง': document.getElementById('cat-pet'),
        'อื่นๆ': document.getElementById('cat-other')
    };

    Object.keys(catButtons).forEach(key => {
        const btn = catButtons[key];
        if (!btn) return;
        if ((key === 'all' && !currentSearchFilters.category) || key === currentSearchFilters.category) {
            btn.classList.remove('bg-white', 'text-gray-500', 'border-gray-100');
            btn.classList.add('bg-primary-100', 'text-primary-700', 'border-primary-200');
        } else {
            btn.classList.remove('bg-primary-100', 'text-primary-700', 'border-primary-200');
            btn.classList.add('bg-white', 'text-gray-500', 'border-gray-100');
        }
    });

    try {
        const token = localStorage.getItem('access_token');
        let isAdmin = false;
        if (token) {
            try {
                const meResp = await fetch(`${API_BASE_URL}/users/me`, { headers: { 'Authorization': `Bearer ${token}` } });
                const user = await meResp.json();
                isAdmin = user && (user.is_admin || user.is_super_admin);
            } catch (e) { }
        }

        const response = await api.getPosts(currentSearchFilters.type, query, currentSearchFilters.category);
        const posts = response.data || [];

        container.innerHTML = '';

        if (posts.length === 0) {
            let emptyMsg = "ไม่พบผลการค้นหา";
            if (query) emptyMsg += ` สำหรับ "${query}"`;
            if (currentSearchFilters.category) emptyMsg += ` ในหมวดหมู่ "${currentSearchFilters.category}"`;
            container.innerHTML = `<div class="col-span-full text-center py-20 text-gray-500 font-medium">${emptyMsg}</div>`;
            return;
        }

        posts.forEach(post => {
            const isLost = post.type === 'lost';
            const badgeColor = isLost ? 'bg-red-500' : 'bg-green-500';
            const badgeText = isLost ? 'ตามหาของหาย' : 'เจอของ';

            const status = post.status || 'published';
            let statusText = 'ประกาศแล้ว';
            let statusColor = 'bg-blue-500';

            if (status === 'pending') {
                statusText = 'รอประกาศ';
                statusColor = 'bg-amber-500';
            } else if (status === 'claimed') {
                statusText = isLost ? 'ได้รับของแล้ว' : 'ส่งคืนเจ้าของแล้ว';
                statusColor = 'bg-gray-500';
            }
            if (post.status_by_name && status !== 'pending') {
                statusText += ` (โดย ${post.status_by_name})`;
            }

            let adminBar = '';
            if (isAdmin) {
                adminBar = `
                <div class="bg-slate-50 border-t border-slate-100 p-2 flex justify-between items-center">
                    <span class="text-[10px] font-bold text-slate-500"><i data-lucide="shield-check" class="w-3 h-3 inline"></i> แอดมิน: เปลี่ยนสถานะ</span>
                    <select onchange="updatePostStatus(event, '${post.id}', this.value)" class="px-2 py-1 bg-white text-[10px] font-bold text-primary-600 rounded-lg border border-slate-200 shadow-sm outline-none cursor-pointer">
                        <option value="pending" ${status === 'pending' ? 'selected' : ''}>รอประกาศ</option>
                        <option value="published" ${status === 'published' ? 'selected' : ''}>ประกาศแล้ว</option>
                        <option value="claimed" ${status === 'claimed' ? 'selected' : ''}>เจ้าของมารับแล้ว</option>
                    </select>
                </div>`;
            }

            const statusDisplay = `<div class="absolute bottom-2 left-2 px-2 py-0.5 ${statusColor} text-[8px] font-extrabold text-white rounded-full uppercase shadow-sm">${statusText}</div>`;

            container.innerHTML += `
            <div class="bg-white rounded-2xl shadow-sm hover:shadow-md border border-gray-100 overflow-hidden transition-all flex flex-col">
                <a href="post-detail.html?id=${post.id}" class="group relative flex h-32">
                    <div class="w-32 h-full bg-gray-100 relative shrink-0">
                        <img src="${(post.image_url && post.image_url.split(',')[0]) || 'https://via.placeholder.com/200?text=No+Image'}" class="w-full h-full object-cover">
                        <div class="absolute top-2 left-2 px-2 py-0.5 ${badgeColor} text-[8px] font-extrabold text-white rounded-full uppercase">${badgeText}</div>
                        ${statusDisplay}
                    </div>
                    <div class="p-4 flex-1 flex flex-col justify-center min-w-0">
                        <div class="flex justify-between items-start">
                            <h4 class="font-bold text-gray-900 line-clamp-1 mb-1 group-hover:text-primary-600 transition-colors">${post.title}</h4>
                        </div>
                        <p class="text-xs text-gray-500 line-clamp-1 mb-2 leading-tight">${post.description}</p>
                        <div class="flex items-center gap-2 text-[10px] text-gray-400 font-medium mt-1">
                            <span class="flex items-center gap-1 bg-gray-50 px-1.5 py-0.5 rounded-md"><i data-lucide="user" class="w-3 h-3 text-slate-400"></i> ${post.author_name || '-'}</span>
                            <span class="flex items-center gap-1 bg-gray-50 px-1.5 py-0.5 rounded-md"><i data-lucide="tag" class="w-3 h-3"></i> ${post.category || 'อื่นๆ'}</span>
                            <span class="flex items-center gap-1"><i data-lucide="map-pin" class="w-3 h-3 text-primary-400"></i> ${post.location}</span>
                        </div>
                    </div>
                </a>
                ${adminBar}
            </div>`;
        });
        lucide.createIcons();
    } catch (err) {
        container.innerHTML = `<div class="col-span-full text-center py-10 text-red-500 font-medium">ไม่สามารถโหลดข้อมูลได้</div>`;
    }
}


async function checkFirstLogin() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    // Only check on index page
    if (!window.location.pathname.includes('index.html') && window.location.pathname !== '/' && !window.location.pathname.endsWith('/frontend/')) return;

    try {
        const resp = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) return;
        const user = await resp.json();

        if (!user.line_social_id) {
            // Show the mandatory LINE ID modal
            const modal = document.getElementById('first-login-modal');
            if (modal) modal.classList.remove('hidden');
        }
    } catch (e) {
        console.warn('checkFirstLogin error:', e);
    }
}

async function saveFirstLineId() {
    const input = document.getElementById('first-line-id-input');
    const lineId = input ? input.value.trim().replace('@', '') : '';
    if (!lineId) { window.ayayaAlert('กรุณากรอก LINE ID ของคุณก่อนครับ', 'warning'); return; }

    try {
        const token = localStorage.getItem('access_token');
        const resp = await fetch(`${API_BASE_URL}/users/me/line-id`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({ line_social_id: lineId })
        });
        if (!resp.ok) throw new Error('บันทึกไม่สำเร็จ');
        document.getElementById('first-login-modal').classList.add('hidden');
    } catch (e) {
        window.ayayaAlert('เกิดข้อผิดพลาด: ' + e.message, 'error');
    }
}

async function initAdminUI() {
    const token = localStorage.getItem('access_token');
    if (!token) return;

    try {
        const resp = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!resp.ok) return;
        const user = await resp.json();

        if (user && (user.is_admin || user.is_super_admin)) {
            const adminUrl = user.is_super_admin ? 'admin/super.html' : 'admin/posts.html';
            
            const desktopLink = document.getElementById('desktop-admin-link');
            if (desktopLink) {
                desktopLink.href = adminUrl;
                desktopLink.classList.remove('hidden');
                desktopLink.classList.add('flex');
            }

            const mobileLink = document.getElementById('mobile-admin-link');
            if (mobileLink) {
                mobileLink.href = adminUrl;
                mobileLink.classList.remove('hidden');
                mobileLink.classList.add('flex');
            }
        }
    } catch (e) {
        console.warn('Admin UI check failed:', e);
    }
}

function updateNavLinks() {
    const token = localStorage.getItem('access_token');
    const hasToken = token && token !== 'undefined' && token !== 'null' && typeof token === 'string' && token.length > 10;

    // Find all links to profile.html and create-post.html
    const protectedLinks = document.querySelectorAll('a[href*="profile.html"], a[href*="create-post.html"]');

    protectedLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (!hasToken) {
                e.preventDefault();
                console.log('Link click prevented: Not logged in');
                window.location.href = 'login.html';
            }
        });
    });
}

// Global function to handle status updates from cards
window.updatePostStatus = async function(event, postId, newStatus) {
    // Prevent default so the <a> tag doesn't trigger
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.ayayaAlert('กรุณาเข้าสู่ระบบก่อน', 'warning');
            return;
        }
        
        const response = await fetch(`${API_BASE_URL}/admin/posts/${postId}/status`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ status: newStatus })
        });
        
        if (!response.ok) {
            throw new Error('Failed to update status');
        }
        
        // Refresh posts after successful update
        const path = window.location.pathname;
        if (path.includes('search.html')) {
            loadSearch();
        } else {
            loadHomePosts('all');
        }
    } catch (err) {
        console.error(err);
        window.ayayaAlert('เกิดข้อผิดพลาดในการเปลี่ยนสถานะ', 'error');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    updateNavLinks();
    initAdminUI();

    if (document.getElementById('search-input')) {
        loadSearch();
    } else if (document.getElementById('post-container')) {
        loadHomePosts();
    }

    loadProfile();
    loadPostDetail();
    checkFirstLogin();
});
