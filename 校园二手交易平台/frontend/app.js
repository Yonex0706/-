/* ═══════════════════════════════════════════
   Campus Trade Platform – Vue 3 App
   ═══════════════════════════════════════════ */

const { createApp, ref, reactive, computed, watch, onMounted, onUnmounted, defineComponent, toRaw } = Vue;

// ── Constants ──
const API_BASE = '';

// ── Store ──
const store = reactive({
  currentUser: JSON.parse(localStorage.getItem('user') || 'null'),
  currentPage: 'home',
  currentItemId: null,
  editItemId: null,
  favoritesSet: new Set(),
  unreadCount: 0,
  navOpen: false,
});

// ══════════════════════════════════════════════
//  Utilities
// ══════════════════════════════════════════════

function highlight(text, keyword) {
  if (!keyword || !text) return text || '';
  const re = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
  return text.replace(re, '<span class="highlight">$1</span>');
}

function formatDate(d) {
  if (!d) return '';
  const date = new Date(d);
  const now = new Date();
  const diff = now - date;
  if (diff < 60000) return '刚刚';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  const y = date.getFullYear(); const m = String(date.getMonth()+1).padStart(2,'0');
  const day = String(date.getDate()).padStart(2,'0');
  return `${y}-${m}-${day}`;
}

function statusLabel(s) {
  return { active: '在售', reserved: '已预定', sold: '已售出',
    pending: '待处理', paid: '已付款', shipped: '已发货', completed: '已完成', cancelled: '已取消' }[s] || s;
}

function statusClass(s) {
  return { active: 'active', reserved: 'reserved', sold: 'sold' }[s] || '';
}

function ratingStars(rating) {
  let s = '';
  for (let i = 1; i <= 5; i++) s += i <= rating ? '★' : '<span class="empty">★</span>';
  return s;
}

// ══════════════════════════════════════════════
//  API Helpers
// ══════════════════════════════════════════════

async function api(url, opts = {}) {
  const res = await fetch(API_BASE + url, {
    headers: { 'Content-Type': 'application/json', ...opts.headers },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || '请求失败');
  }
  return res.json();
}

function apiForm(url, formData) {
  return fetch(API_BASE + url, { method: 'POST', body: formData }).then(r => r.json());
}

// ── Auth ──
function register(data) { return api('/api/register', { method: 'POST', body: JSON.stringify(data) }); }
function login(data) { return api('/api/login', { method: 'POST', body: JSON.stringify(data) }); }

// ── Items ──
function fetchItems(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== null && v !== undefined && v !== '') q.set(k, v); });
  return api(`/api/items/?${q}`);
}
function fetchItem(id, userId) {
  let url = `/api/items/${id}`;
  if (userId) url += `?user_id=${userId}`;
  return api(url);
}
function createItem(data) { return api('/api/items/', { method: 'POST', body: JSON.stringify(data) }); }
function updateItem(id, data) { return api(`/api/items/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
function deleteItemApi(id, userId) { return api(`/api/items/${id}?user_id=${userId}`, { method: 'DELETE' }); }
function fetchUserItems(userId, page = 1) { return api(`/api/users/${userId}/items?page=${page}&page_size=12`); }
function fetchHotItems() { return api('/api/items/hot?limit=8'); }

// ── Categories ──
function fetchCategories() { return api('/api/categories'); }

// ── Favorites ──
function toggleFavApi(data) { return api('/api/favorites/', { method: 'POST', body: JSON.stringify(data) }); }
function fetchFavorites(userId, page = 1) { return api(`/api/users/${userId}/favorites?page=${page}&page_size=12`); }

// ── Messages ──
function fetchMessages(userId, otherId) {
  let url = `/api/messages/?user_id=${userId}`;
  if (otherId) url += `&other_id=${otherId}`;
  return api(url);
}
function sendMsg(data) { return api('/api/messages/', { method: 'POST', body: JSON.stringify(data) }); }
function fetchUnreadCount(userId) { return api(`/api/messages/unread-count?user_id=${userId}`); }

// ── Reviews ──
function fetchReviews(params) {
  const q = new URLSearchParams(params);
  return api(`/api/reviews/?${q}`);
}
function createReview(data) { return api('/api/reviews/', { method: 'POST', body: JSON.stringify(data) }); }
function fetchUserRating(userId) { return api(`/api/users/${userId}/rating`); }

// ── Orders ──
function createOrder(data) { return api('/api/orders/', { method: 'POST', body: JSON.stringify(data) }); }
function fetchOrders(userId, asBuyer = true) { return api(`/api/orders/?user_id=${userId}&as_buyer=${asBuyer}`); }
function updateOrder(id, data) { return api(`/api/orders/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }

// ── Stats ──
function fetchStats() { return api('/api/stats'); }

// ── Profile ──
function updateProfile(userId, data) { return api(`/api/users/${userId}/profile`, { method: 'PUT', body: JSON.stringify(data) }); }

// ── Posts ──
function fetchPosts(userId) { return api(`/api/users/${userId}/posts`); }
function createPost(data) { return api('/api/posts/', { method: 'POST', body: JSON.stringify(data) }); }
function deletePostApi(postId, userId) { return api(`/api/posts/${postId}?user_id=${userId}`, { method: 'DELETE' }); }

// ── Upload ──
async function uploadImage(file) {
  const fd = new FormData(); fd.append('file', file);
  return apiForm('/api/upload', fd);
}


// ══════════════════════════════════════════════
//  Components
// ══════════════════════════════════════════════

// ── Pagination Widget ──
const PaginationWidget = {
  template: `
    <div class="pagination" v-if="totalPages > 1">
      <button :disabled="page <= 1" @click="$emit('page-change', page - 1)">上一页</button>
      <template v-for="p in visiblePages" :key="p">
        <button v-if="p === '...'" disabled>...</button>
        <button v-else :class="{ active: p === page }" @click="$emit('page-change', p)">{{ p }}</button>
      </template>
      <button :disabled="page >= totalPages" @click="$emit('page-change', page + 1)">下一页</button>
    </div>
  `,
  props: { page: Number, totalPages: Number },
  emits: ['page-change'],
  computed: {
    visiblePages() {
      const { page, totalPages } = this;
      if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
      const pages = [];
      if (page <= 4) {
        for (let i = 1; i <= 5; i++) pages.push(i);
        pages.push('...', totalPages);
      } else if (page >= totalPages - 3) {
        pages.push(1, '...');
        for (let i = totalPages - 4; i <= totalPages; i++) pages.push(i);
      } else {
        pages.push(1, '...', page - 1, page, page + 1, '...', totalPages);
      }
      return pages;
    },
  },
};

// ── Item Card ──
const ItemCard = {
  template: `
    <div class="item-card card">
      <img class="card-img" :src="item.image_url || 'https://picsum.photos/seed/default/400/300'" :alt="item.title" @error="onImgError" @click="viewDetail">
      <div class="card-body">
        <div class="card-title" @click="viewDetail" style="cursor:pointer">
          <span v-html="highlight(item.title, keyword)"></span>
        </div>
        <div>
          <span class="card-price">¥{{ item.price.toFixed(2) }}</span>
          <span class="card-original-price" v-if="item.original_price">¥{{ item.original_price.toFixed(2) }}</span>
        </div>
        <div class="card-meta">
          <span><span class="tag">{{ item.category_name || '未分类' }}</span></span>
          <div class="flex-between gap-2" style="align-items:center">
            <span>👁 {{ item.view_count }}</span>
            <button class="fav-btn" :class="{ active: item.is_favorited }"
              @click.stop="toggleFav" :disabled="!store.currentUser" :title="item.is_favorited ? '取消收藏' : '收藏'">
              {{ item.is_favorited ? '❤️' : '🤍' }}
            </button>
          </div>
        </div>
        <div style="font-size:.75rem;color:#999;margin-top:4px">{{ item.seller_name }} · {{ formatDate(item.created_at) }}</div>
      </div>
    </div>
  `,
  props: { item: Object, keyword: { type: String, default: '' } },
  emits: ['navigate', 'fav-change'],
  setup(props, { emit }) {
    const viewDetail = () => {
      store.currentItemId = props.item.id;
      emit('navigate', 'detail');
    };
    const onImgError = (e) => { e.target.src = 'https://picsum.photos/seed/error/400/300'; };
    const handleToggleFav = async () => {
      if (!store.currentUser) return;
      const res = await toggleFavApi({ user_id: store.currentUser.id, item_id: props.item.id });
      props.item.is_favorited = res.favorited;
      emit('fav-change', { itemId: props.item.id, favorited: res.favorited });
    };
    return { viewDetail, onImgError, toggleFav: handleToggleFav, store, highlight, formatDate };
  },
};

// ── Review Card ──
const ReviewCard = {
  template: `
    <div class="review-card">
      <div class="header">
        <span><strong>{{ review.reviewer_name || '匿名' }}</strong></span>
        <span>{{ formatDate(review.created_at) }}</span>
      </div>
      <div v-html="ratingStars(review.rating)" class="stars mb-4"></div>
      <p v-if="review.comment" style="font-size:.9rem;">{{ review.comment }}</p>
    </div>
  `,
  props: { review: Object },
  setup: () => ({ formatDate, ratingStars }),
};

// ══════════════════════════════════════════════
//  Pages
// ══════════════════════════════════════════════

// ── Home Page ──
const HomePage = {
  template: `
    <div>
      <!-- Filter Panel -->
      <div class="filter-panel">
        <div class="filter-row">
          <div class="form-group">
            <label>关键词</label>
            <input class="form-control" v-model="filters.keyword" placeholder="搜索物品..." @input="debounceSearch">
          </div>
          <div class="form-group">
            <label>分类</label>
            <select class="form-control" v-model="filters.category_id" @change="doSearch">
              <option value="">全部分类</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>最低价</label>
            <input class="form-control" type="number" min="0" v-model.number="filters.min_price" placeholder="¥0" @input="debounceSearch">
          </div>
          <div class="form-group">
            <label>最高价</label>
            <input class="form-control" type="number" min="0" v-model.number="filters.max_price" placeholder="¥不限" @input="debounceSearch">
          </div>
          <div class="form-group">
            <label>排序</label>
            <select class="form-control" v-model="filters.sort_by" @change="doSearch">
              <option value="created_at">最新</option>
              <option value="price">价格</option>
              <option value="view_count">热度</option>
            </select>
          </div>
          <div class="form-group">
            <label>顺序</label>
            <select class="form-control" v-model="filters.sort_order" @change="doSearch">
              <option value="desc">降序</option>
              <option value="asc">升序</option>
            </select>
          </div>
          <div class="filter-actions">
            <button class="btn btn-primary" @click="doSearch">筛选</button>
            <button class="btn btn-outline" @click="resetFilters">重置</button>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div class="state-msg" v-if="loading">
        <div class="spinner"></div>
        <h3>加载中...</h3>
      </div>

      <!-- Error -->
      <div class="state-msg" v-else-if="error">
        <div class="icon">😵</div>
        <h3>{{ error }}</h3>
        <button class="btn btn-primary mt-4" @click="loadItems">重试</button>
      </div>

      <!-- Empty -->
      <div class="state-msg" v-else-if="items.length === 0">
        <div class="icon">📦</div>
        <h3>暂无物品</h3>
        <p v-if="store.currentUser" style="margin-top:8px">
          <button class="btn btn-primary" @click="$emit('navigate', 'publish')">发布第一件物品</button>
        </p>
      </div>

      <!-- Item Grid -->
      <div class="item-grid" v-else>
        <ItemCard v-for="item in items" :key="item.id" :item="item" :keyword="filters.keyword"
          @navigate="(p) => $emit('navigate', p)" @fav-change="onFavChange" />
      </div>

      <!-- Pagination -->
      <PaginationWidget :page="page" :total-pages="totalPages" @page-change="goPage" />
    </div>
  `,
  components: { ItemCard, PaginationWidget },
  emits: ['navigate', 'refresh-fav'],
  setup(props, { emit }) {
    const items = ref([]);
    const categories = ref([]);
    const page = ref(1);
    const totalPages = ref(1);
    const loading = ref(false);
    const error = ref('');

    let debounceTimer = null;
    const filters = reactive({
      keyword: '', category_id: '', min_price: null, max_price: null,
      sort_by: 'created_at', sort_order: 'desc',
    });

    function debounceSearch() {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(doSearch, 400);
    }

    async function loadItems() {
      loading.value = true; error.value = '';
      try {
        const params = {
          page: page.value, page_size: 12,
          keyword: filters.keyword || undefined,
          category_id: filters.category_id || undefined,
          min_price: filters.min_price || undefined,
          max_price: filters.max_price || undefined,
          sort_by: filters.sort_by,
          sort_order: filters.sort_order,
          user_id: store.currentUser?.id,
        };
        const data = await fetchItems(params);
        items.value = data.items;
        page.value = data.page;
        totalPages.value = data.total_pages;
      } catch (e) {
        error.value = e.message;
      } finally {
        loading.value = false;
      }
    }

    function doSearch() { page.value = 1; loadItems(); }
    function goPage(p) { page.value = p; loadItems(); window.scrollTo({ top: 0, behavior: 'smooth' }); }

    function resetFilters() {
      filters.keyword = ''; filters.category_id = '';
      filters.min_price = null; filters.max_price = null;
      filters.sort_by = 'created_at'; filters.sort_order = 'desc';
      doSearch();
    }

    function onFavChange({ itemId, favorited }) {
      store.favoritesSet[itemId] = favorited;
      emit('refresh-fav');
    }

    onMounted(async () => {
      categories.value = await fetchCategories();
      loadItems();
    });

    return { items, categories, page, totalPages, loading, error, filters, loadItems, doSearch, goPage, resetFilters, debounceSearch, onFavChange, store };
  },
};

// ── Item Detail Page ──
const ItemDetail = {
  template: `
    <div>
      <a href="#" @click.prevent="$emit('navigate', 'home')" style="display:inline-block;margin-bottom:16px">&larr; 返回列表</a>
      <div class="state-msg" v-if="loading">
        <div class="spinner"></div><h3>加载中...</h3>
      </div>
      <div class="state-msg" v-else-if="error">
        <div class="icon">😵</div><h3>{{ error }}</h3>
        <button class="btn btn-primary mt-4" @click="loadItem">重试</button>
      </div>
      <template v-else-if="item">
        <div class="detail">
          <!-- Gallery -->
          <div class="detail-gallery">
            <img class="main-img" :src="currentImg" :alt="item.title" @error="e=>e.target.src='https://picsum.photos/seed/error2/400/300'" @click="showGallery=true" style="cursor:zoom-in">
            <div class="detail-thumbs" v-if="allImages.length > 1">
              <img v-for="(img, i) in allImages" :key="i" :src="img" :class="{ active: currentImg === img }" @click="currentImg = img" @error="e=>e.target.src='https://picsum.photos/seed/thumb/64/64'">
            </div>
          </div>
          <!-- Info -->
          <div class="detail-info">
            <h1>{{ item.title }}</h1>
            <div><span class="detail-status" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span></div>
            <div class="detail-price">
              ¥{{ item.price.toFixed(2) }}
              <span class="detail-original" v-if="item.original_price">¥{{ item.original_price.toFixed(2) }}</span>
            </div>
            <div class="detail-meta">
              <span>📂 {{ item.category_name || '未分类' }}</span>
              <span>👤 {{ item.seller_name }}</span>
              <span>👁 {{ item.view_count }} 次浏览</span>
              <span>📅 {{ formatDate(item.created_at) }}</span>
            </div>
            <!-- Seller Rating -->
            <div v-if="sellerRating !== null" class="mb-4">
              <span v-html="ratingStars(sellerRating)" class="stars"></span>
              <span style="font-size:.8rem;color:#999;margin-left:4px">({{ sellerReviewCount }}条评价)</span>
            </div>
            <p class="detail-desc">{{ item.description || '暂无描述' }}</p>
            <div class="detail-actions">
              <button class="btn btn-outline" :class="{ active: item.is_favorited }" @click="toggleFav" v-if="store.currentUser">
                {{ item.is_favorited ? '❤️ 已收藏' : '🤍 收藏' }}
              </button>
              <button class="btn btn-success" @click="buyItem" v-if="canBuy">💳 立即购买</button>
              <button class="btn btn-primary" @click="contactSeller" v-if="canContact">✉️ 联系卖家</button>
              <button class="btn btn-warning" @click="goEdit" v-if="canEdit">✏️ 编辑</button>
              <button class="btn btn-danger" @click="deleteItem" v-if="canEdit">🗑️ 删除</button>
            </div>
          </div>
        </div>

        <!-- Reviews -->
        <div style="margin-top:24px;background:#fff;border-radius:12px;padding:24px;box-shadow:0 2px 12px rgba(0,0,0,.06)">
          <div class="flex-between mb-4" style="align-items:center;flex-wrap:wrap">
            <h3 style="margin-bottom:0">商品评价 ({{ reviews.length }})</h3>
            <div v-if="reviews.length > 0" style="display:flex;align-items:center;gap:8px">
              <span v-html="ratingStars(Math.round(itemAvgRating))" class="stars" style="font-size:1.2rem"></span>
              <span style="font-size:.9rem;color:#666">{{ itemAvgRating.toFixed(1) }} 分</span>
            </div>
          </div>
          <ReviewCard v-for="r in reviews" :key="r.id" :review="r" />
          <div v-if="reviews.length === 0" style="text-align:center;color:#999;padding:20px">暂无评价</div>
          <!-- Write Review -->
          <div v-if="canReview" style="margin-top:20px;padding-top:20px;border-top:1px solid #eee">
            <h4 style="margin-bottom:12px">写评价</h4>
            <div class="form-group">
              <label>评分</label>
              <select class="form-control" v-model.number="newReview.rating" style="width:120px">
                <option v-for="n in 5" :key="n" :value="n">{{ '★'.repeat(n) + '☆'.repeat(5-n) }}</option>
              </select>
            </div>
            <div class="form-group">
              <label>评价内容</label>
              <textarea class="form-control" v-model="newReview.comment" placeholder="分享你的交易体验..." rows="3"></textarea>
            </div>
            <button class="btn btn-primary" @click="submitReview" :disabled="submittingReview">提交评价</button>
          </div>
        </div>
      </template>

      <!-- Gallery Modal -->
      <div class="gallery-modal" v-if="showGallery" @click="showGallery=false">
        <img :src="currentImg" @click.stop>
      </div>
    </div>
  `,
  components: { ReviewCard },
  emits: ['navigate'],
  setup(props, { emit }) {
    const item = ref(null);
    const loading = ref(true);
    const error = ref('');
    const allImages = computed(() => {
      const urls = [];
      if (item.value?.image_url) urls.push(item.value.image_url);
      if (item.value?.images) item.value.images.forEach(img => urls.push(img.image_url));
      return urls.length ? urls : ['https://picsum.photos/seed/none/400/300'];
    });
    const currentImg = ref('');
    const showGallery = ref(false);
    const reviews = ref([]);
    const sellerRating = ref(null);
    const sellerReviewCount = ref(0);
    const newReview = reactive({ rating: 5, comment: '' });
    const submittingReview = ref(false);

    const itemAvgRating = computed(() => {
      if (reviews.value.length === 0) return 0;
      const sum = reviews.value.reduce((s, r) => s + r.rating, 0);
      return sum / reviews.value.length;
    });
    const canBuy = computed(() =>
      store.currentUser && item.value && item.value.status === 'active'
      && store.currentUser.id !== item.value.seller_id
    );
    const canContact = computed(() => store.currentUser && item.value && store.currentUser.id !== item.value.seller_id);
    const canEdit = computed(() => store.currentUser && item.value && store.currentUser.id === item.value.seller_id);
    const canReview = computed(() => store.currentUser && item.value && store.currentUser.id !== item.value.seller_id
      && item.value.status === 'sold');

    async function loadItem() {
      loading.value = true; error.value = '';
      try {
        const data = await fetchItem(store.currentItemId, store.currentUser?.id);
        item.value = data;
        currentImg.value = allImages.value[0];
        // Load reviews
        reviews.value = await fetchReviews({ item_id: store.currentItemId });
        // Load seller rating
        if (data.seller_id) {
          const ratingData = await fetchUserRating(data.seller_id);
          sellerRating.value = ratingData.avg_rating;
          sellerReviewCount.value = ratingData.total_reviews;
        }
      } catch (e) { error.value = e.message; }
      finally { loading.value = false; }
    }

    async function handleToggleFav() {
      if (!store.currentUser) return;
      const res = await toggleFavApi({ user_id: store.currentUser.id, item_id: item.value.id });
      item.value.is_favorited = res.favorited;
    }

    async function buyItem() {
      try {
        await createOrder({ buyer_id: store.currentUser.id, item_id: item.value.id });
        alert('购买请求已发送！等待卖家确认。');
        loadItem();
      } catch (e) { alert(e.message); }
    }

    function contactSeller() {
      store.currentItemId = item.value.id;
      emit('navigate', 'chat');
    }

    function goEdit() {
      store.editItemId = item.value.id;
      emit('navigate', 'publish');
    }

    async function deleteItem() {
      if (!confirm('确认删除该物品？')) return;
      try {
        await deleteItemApi(item.value.id, store.currentUser.id);
        alert('删除成功');
        emit('navigate', 'my-items');
      } catch (e) { alert(e.message); }
    }

    async function submitReview() {
      if (!store.currentUser || !item.value) return;
      submittingReview.value = true;
      try {
        await createReview({
          reviewer_id: store.currentUser.id,
          reviewee_id: item.value.seller_id,
          item_id: item.value.id,
          rating: newReview.rating,
          comment: newReview.comment,
        });
        alert('评价成功！');
        newReview.comment = '';
        reviews.value = await fetchReviews({ item_id: store.currentItemId });
      } catch (e) { alert(e.message); }
      finally { submittingReview.value = false; }
    }

    onMounted(loadItem);
    return {
      item, loading, error, allImages, currentImg, showGallery,
      reviews, sellerRating, sellerReviewCount, newReview, submittingReview,
      canBuy, canContact, canEdit, canReview, itemAvgRating, store,
      toggleFav: handleToggleFav, buyItem, contactSeller, goEdit, deleteItem, submitReview,
      formatDate, statusLabel, statusClass, ratingStars,
    };
  },
};

// ── Item Form (Publish / Edit) ──
const ItemForm = {
  template: `
    <div class="auth-box" style="max-width:600px">
      <h2>{{ isEdit ? '编辑物品' : '发布物品' }}</h2>
      <div class="form-group">
        <label>标题 *</label>
        <input class="form-control" :class="{ error: errors.title }" v-model="form.title" placeholder="物品名称">
        <div class="error-text" v-if="errors.title">{{ errors.title }}</div>
      </div>
      <div class="form-group">
        <label>描述</label>
        <textarea class="form-control" v-model="form.description" placeholder="描述物品成色、规格等信息..." rows="4"></textarea>
      </div>
      <div class="form-group">
        <label>价格 *</label>
        <input class="form-control" :class="{ error: errors.price }" type="number" step="0.01" min="0.01" v-model.number="form.price" placeholder="0.00">
        <div class="error-text" v-if="errors.price">{{ errors.price }}</div>
      </div>
      <div class="form-group">
        <label>原价</label>
        <input class="form-control" type="number" step="0.01" min="0" v-model.number="form.original_price" placeholder="0.00">
      </div>
      <div class="form-group">
        <label>分类</label>
        <select class="form-control" v-model="form.category_id">
          <option value="">请选择分类</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="form-group">
        <label>图片URL</label>
        <input class="form-control" v-model="form.image_url" placeholder="https://...">
      </div>
      <div class="form-group">
        <label>上传图片</label>
        <input type="file" accept="image/*" @change="onFileSelect">
        <div v-if="uploading" class="spinner" style="margin-top:8px"></div>
      </div>
      <div class="error-text mb-4" v-if="errors.submit">{{ errors.submit }}</div>
      <div style="display:flex;gap:12px">
        <button class="btn btn-primary" style="flex:1" @click="submit" :disabled="submitting">
          {{ submitting ? '提交中...' : (isEdit ? '保存修改' : '发布物品') }}
        </button>
        <button class="btn btn-outline" @click="$emit('navigate', 'home')">取消</button>
      </div>
    </div>
  `,
  emits: ['navigate'],
  setup(props, { emit }) {
    const isEdit = computed(() => !!store.editItemId);
    const categories = ref([]);
    const submitting = ref(false);
    const uploading = ref(false);
    const form = reactive({
      title: '', description: '', price: null, original_price: null,
      category_id: '', image_url: '',
    });
    const errors = reactive({ title: '', price: '', submit: '' });

    function validate() {
      let valid = true;
      errors.title = ''; errors.price = ''; errors.submit = '';
      if (!form.title.trim()) { errors.title = '请输入标题'; valid = false; }
      if (!form.price || form.price <= 0) { errors.price = '请输入有效价格'; valid = false; }
      return valid;
    }

    async function submit() {
      if (!validate()) return;
      submitting.value = true;
      try {
        const data = {
          title: form.title.trim(), description: form.description,
          price: form.price, original_price: form.original_price || null,
          category_id: form.category_id || null, image_url: form.image_url || null,
          seller_id: store.currentUser.id,
        };
        if (isEdit.value) {
          await updateItem(store.editItemId, data);
          alert('修改成功！');
        } else {
          const item = await createItem(data);
          alert('发布成功！');
          store.editItemId = null;
        }
        emit('navigate', 'my-items');
      } catch (e) { errors.submit = e.message; }
      finally { submitting.value = false; }
    }

    async function onFileSelect(e) {
      const file = e.target.files[0];
      if (!file) return;
      uploading.value = true;
      try {
        const res = await uploadImage(file);
        form.image_url = res.url;
      } catch (e) { alert('上传失败: ' + e.message); }
      finally { uploading.value = false; }
    }

    onMounted(async () => {
      categories.value = await fetchCategories();
      if (store.editItemId) {
        const item = await fetchItem(store.editItemId);
        form.title = item.title;
        form.description = item.description || '';
        form.price = item.price;
        form.original_price = item.original_price || null;
        form.category_id = item.category_id || '';
        form.image_url = item.image_url || '';
      }
    });

    return { isEdit, categories, form, errors, submitting, uploading, validate, submit, onFileSelect, store };
  },
};

// ── My Items ──
const MyItemsPage = {
  template: `
    <div>
      <div class="flex-between mb-4" style="align-items:center">
        <h2>我的发布</h2>
        <button class="btn btn-primary" @click="goPublish">+ 发布新物品</button>
      </div>
      <div class="state-msg" v-if="loading"><div class="spinner"></div><h3>加载中...</h3></div>
      <div class="state-msg" v-else-if="items.length === 0">
        <div class="icon">📦</div><h3>还没有发布任何物品</h3>
        <button class="btn btn-primary mt-4" @click="goPublish">发布第一件</button>
      </div>
      <div v-else>
        <div class="item-card card" v-for="item in items" :key="item.id" style="display:flex;margin-bottom:12px;overflow:visible">
          <img :src="item.image_url || 'https://picsum.photos/seed/default/400/300'" style="width:120px;height:120px;object-fit:cover;flex-shrink:0" @error="e=>e.target.src='https://picsum.photos/seed/err/400/300'">
          <div style="flex:1;padding:14px;display:flex;flex-direction:column;justify-content:space-between">
            <div>
              <h4 style="margin-bottom:4px;cursor:pointer" @click="viewDetail(item)">{{ item.title }}</h4>
              <div style="font-size:.85rem;color:#888">
                ¥{{ item.price.toFixed(2) }} · {{ item.category_name || '未分类' }} · 👁 {{ item.view_count }}
              </div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px">
              <span class="detail-status" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
              <select class="form-control" style="width:auto;padding:4px 8px;font-size:.8rem" v-model="item.status" @change="changeStatus(item)">
                <option value="active">在售</option>
                <option value="reserved">已预定</option>
                <option value="sold">已售出</option>
              </select>
              <button class="btn btn-sm btn-outline" @click="editItem(item)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="removeItem(item)">删除</button>
            </div>
          </div>
        </div>
        <PaginationWidget :page="page" :total-pages="totalPages" @page-change="goPage" />
      </div>
    </div>
  `,
  components: { PaginationWidget },
  emits: ['navigate'],
  setup(props, { emit }) {
    const items = ref([]);
    const page = ref(1);
    const totalPages = ref(1);
    const loading = ref(true);

    async function loadItems() {
      loading.value = true;
      try {
        const data = await fetchUserItems(store.currentUser.id, page.value);
        items.value = data.items;
        page.value = data.page;
        totalPages.value = data.total_pages;
      } catch (e) { alert(e.message); }
      finally { loading.value = false; }
    }

    function goPage(p) { page.value = p; loadItems(); }

    function goPublish() {
      store.editItemId = null;
      emit('navigate', 'publish');
    }

    function editItem(item) {
      store.editItemId = item.id;
      emit('navigate', 'publish');
    }

    function viewDetail(item) {
      store.currentItemId = item.id;
      emit('navigate', 'detail');
    }

    async function removeItem(item) {
      if (!confirm(`确认删除「${item.title}」？`)) return;
      try {
        await deleteItemApi(item.id, store.currentUser.id);
        loadItems();
      } catch (e) { alert(e.message); }
    }

    async function changeStatus(item) {
      try {
        await updateItem(item.id, { status: item.status });
      } catch (e) { alert(e.message); }
    }

    onMounted(loadItems);
    return { items, page, totalPages, loading, loadItems, goPage, goPublish, editItem, viewDetail, removeItem, changeStatus, statusLabel, statusClass };
  },
};

// ── Favorites Page ──
const FavoritesPage = {
  template: `
    <div>
      <h2 class="mb-4">我的收藏</h2>
      <div class="state-msg" v-if="loading"><div class="spinner"></div><h3>加载中...</h3></div>
      <div class="state-msg" v-else-if="items.length === 0">
        <div class="icon">💔</div><h3>还没有收藏任何物品</h3>
        <p style="margin-top:8px"><a href="#" @click.prevent="$emit('navigate', 'home')">去逛逛</a></p>
      </div>
      <div class="item-grid" v-else>
        <ItemCard v-for="item in items" :key="item.id" :item="item"
          @navigate="(p) => $emit('navigate', p)" @fav-change="onFavChange" />
      </div>
      <PaginationWidget :page="page" :total-pages="totalPages" @page-change="goPage" />
    </div>
  `,
  components: { ItemCard, PaginationWidget },
  emits: ['navigate', 'refresh-fav'],
  setup(props, { emit }) {
    const items = ref([]);
    const page = ref(1);
    const totalPages = ref(1);
    const loading = ref(true);

    async function loadItems() {
      loading.value = true;
      try {
        const data = await fetchFavorites(store.currentUser.id, page.value);
        items.value = data.items;
        page.value = data.page;
        totalPages.value = data.total_pages;
      } catch (e) { alert(e.message); }
      finally { loading.value = false; }
    }

    function goPage(p) { page.value = p; loadItems(); }
    function onFavChange({ itemId, favorited }) {
      if (!favorited) items.value = items.value.filter(i => i.id !== itemId);
      emit('refresh-fav');
    }

    onMounted(loadItems);
    return { items, page, totalPages, loading, loadItems, goPage, onFavChange };
  },
};

// ── Profile Page ──
const ProfilePage = {
  template: `
    <div class="profile-page">
      <div v-if="!store.currentUser" class="state-msg">
        <div class="icon">🔒</div><h3>请先登录</h3>
      </div>
      <template v-else-if="userData">
        <!-- Card 1: Avatar + Nickname + @username -->
        <div class="profile-card">
          <div class="profile-top-row">
            <div class="profile-avatar-wrap" @click="triggerAvatarUpload">
              <img v-if="userData.avatar_url" :src="userData.avatar_url" @error="e=>e.target.src='https://picsum.photos/seed/avatar/120/120'">
              <div v-else class="avatar-placeholder">{{ (userData.real_name || userData.username)[0] }}</div>
              <div class="avatar-overlay">更换头像</div>
            </div>
            <div class="profile-identity">
              <div class="nickname-row">
                <template v-if="editing.real_name">
                  <input v-model="form.real_name" class="nickname-input" placeholder="昵称" />
                  <button class="icon-btn confirm-btn" @click="editing.real_name = false">✓</button>
                </template>
                <template v-else>
                  <h2 class="nickname-text">{{ form.real_name || '未设置昵称' }}</h2>
                  <button class="icon-btn edit-btn" @click="startEdit($event, 'real_name')">✏️</button>
                </template>
              </div>
              <span class="username-tag">@{{ userData.username }}</span>
            </div>
          </div>
        </div>

        <!-- Card 2: Editable Info Fields -->
        <div class="profile-card">
          <h3>个人信息</h3>
          <div class="info-field" v-for="f in infoFields" :key="f.key">
            <label>{{ f.label }}</label>
            <div class="field-value-row">
              <template v-if="editing[f.key]">
                <input v-model="form[f.key]" :placeholder="f.placeholder" class="field-input" />
                <button class="icon-btn confirm-btn" @click="editing[f.key] = false">✓</button>
              </template>
              <template v-else>
                <span class="field-text" :class="{ 'text-muted': !form[f.key] }">{{ form[f.key] || f.placeholder }}</span>
                <button class="icon-btn edit-btn" @click="startEdit($event, f.key)">✏️</button>
              </template>
            </div>
          </div>
        </div>

        <!-- Card 3: Stats -->
        <div class="profile-card">
          <div class="stats-row">
            <div class="stat-item"><span class="num">{{ stats.itemsCount }}</span><span class="label">发布</span></div>
            <div class="stat-item"><span class="num">{{ stats.favCount }}</span><span class="label">收藏</span></div>
            <div class="stat-item"><span class="num">{{ stats.rating }}</span><span class="label">评分</span></div>
            <div class="stat-item"><span class="num">{{ posts.length }}</span><span class="label">动态</span></div>
          </div>
        </div>

        <!-- Card 4: Posts Section -->
        <div class="profile-card">
          <div class="section-header">
            <h3>我的动态</h3>
            <button class="btn btn-primary btn-sm" @click="showPostInput = !showPostInput">+ 发动态</button>
          </div>
          <div v-if="showPostInput" class="post-input-box">
            <textarea v-model="newPostContent" placeholder="分享你的校园生活..." rows="3" maxlength="500"></textarea>
            <div class="post-input-actions">
              <span class="char-count">{{ newPostContent.length }}/500</span>
              <button class="btn btn-primary btn-sm" @click="submitPost" :disabled="!newPostContent.trim() || posting">发布</button>
            </div>
          </div>
          <div v-if="posts.length === 0" class="empty-posts">
            <p>还没有发布动态</p>
          </div>
          <div v-for="post in posts" :key="post.id" class="post-item">
            <div class="post-header">
              <span class="name">{{ post.author_name || userData.username }}</span>
              <span class="time">{{ formatDate(post.created_at) }}</span>
              <button class="del-btn" @click="removePost(post.id)">删除</button>
            </div>
            <p class="post-content">{{ post.content }}</p>
          </div>
        </div>

        <!-- Save All Button -->
        <button class="btn btn-primary save-all-btn" @click="saveProfile" :disabled="saving">
          {{ saving ? '保存中...' : '保存所有修改' }}
        </button>
        <div v-if="saveError" class="error-text" style="text-align:center;margin-top:12px">{{ saveError }}</div>
      </template>
      <div v-else class="state-msg"><div class="spinner"></div><h3>加载中...</h3></div>
    </div>
  `,
  emits: ['navigate'],
  setup(props, { emit }) {
    const userData = ref(null);
    const saving = ref(false);
    const saveError = ref('');
    const posts = ref([]);
    const showPostInput = ref(false);
    const newPostContent = ref('');
    const posting = ref(false);
    const stats = reactive({ itemsCount: 0, favCount: 0, rating: 0 });
    const form = reactive({ real_name: '', student_id: '', phone: '', email: '', college: '', avatar_url: '', bio: '' });
    const editing = reactive({ real_name: false, college: false, student_id: false, phone: false, email: false });

    const infoFields = [
      { key: 'college', label: '学院', placeholder: '请输入学院' },
      { key: 'student_id', label: '学号', placeholder: '请输入学号' },
      { key: 'phone', label: '手机', placeholder: '请输入手机号' },
      { key: 'email', label: '邮箱', placeholder: '请输入邮箱' },
    ];

    function startEdit(e, field) {
      editing[field] = true;
      Vue.nextTick(() => {
        const row = e.target.closest('.nickname-row, .field-value-row');
        const input = row && row.querySelector('input');
        if (input) input.focus();
      });
    }

    async function loadProfile() {
      try {
        const data = await api(`/api/users/${store.currentUser.id}`);
        userData.value = data;
        form.real_name = data.real_name || '';
        form.student_id = data.student_id || '';
        form.phone = data.phone || '';
        form.email = data.email || '';
        form.college = data.college || '';
        form.avatar_url = data.avatar_url || '';
        form.bio = data.bio || '';
        const itemsData = await fetchUserItems(store.currentUser.id);
        stats.itemsCount = itemsData.total || 0;
        const favData = await fetchFavorites(store.currentUser.id);
        stats.favCount = favData.total || 0;
        const ratingData = await fetchUserRating(store.currentUser.id);
        stats.rating = ratingData.avg_rating || 0;
      } catch (e) { /* ignore */ }
    }

    async function loadPosts() {
      try { posts.value = await fetchPosts(store.currentUser.id); }
      catch (e) { /* ignore */ }
    }

    async function saveProfile() {
      saving.value = true; saveError.value = '';
      try {
        const data = await updateProfile(store.currentUser.id, { ...form });
        userData.value = data;
        Object.keys(editing).forEach(k => editing[k] = false);
      } catch (e) { saveError.value = e.message; }
      finally { saving.value = false; }
    }

    function triggerAvatarUpload() {
      const input = document.createElement('input');
      input.type = 'file'; input.accept = 'image/*';
      input.onchange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
          const res = await uploadImage(file);
          form.avatar_url = res.url;
          await saveProfile();
        } catch (e) { alert('上传失败'); }
      };
      input.click();
    }

    async function submitPost() {
      if (!newPostContent.value.trim()) return;
      posting.value = true;
      try {
        await createPost({ user_id: store.currentUser.id, content: newPostContent.value });
        newPostContent.value = '';
        showPostInput.value = false;
        await loadPosts();
      } catch (e) { alert(e.message); }
      finally { posting.value = false; }
    }

    async function removePost(postId) {
      if (!confirm('确认删除此动态？')) return;
      try { await deletePostApi(postId, store.currentUser.id); await loadPosts(); }
      catch (e) { alert(e.message); }
    }

    onMounted(() => { loadProfile(); loadPosts(); });

    return { store, userData, form, editing, saving, saveError, posts, showPostInput, newPostContent, posting, stats, infoFields,
      startEdit, saveProfile, triggerAvatarUpload, submitPost, removePost, formatDate };
  },
};

// ── Login / Register Page ──
const LoginPage = {
  template: `
    <div class="auth-box">
      <h2>{{ isLogin ? '登录' : '注册' }}</h2>
      <div class="form-group">
        <label>用户名</label>
        <input class="form-control" v-model="form.username" placeholder="请输入用户名">
      </div>
      <div class="form-group" v-if="!isLogin">
        <label>邮箱</label>
        <input class="form-control" v-model="form.email" placeholder="选填">
      </div>
      <div class="form-group">
        <label>密码</label>
        <input class="form-control" type="password" v-model="form.password" placeholder="请输入密码">
      </div>
      <div class="error-text mb-4" v-if="error">{{ error }}</div>
      <button class="btn btn-primary" style="width:100%" @click="submit" :disabled="submitting">
        {{ submitting ? '处理中...' : (isLogin ? '登录' : '注册') }}
      </button>
      <div class="auth-toggle">
        {{ isLogin ? '没有账号？' : '已有账号？' }}
        <a href="#" @click.prevent="isLogin = !isLogin; error = ''">
          {{ isLogin ? '去注册' : '去登录' }}
        </a>
      </div>
    </div>
  `,
  emits: ['navigate'],
  setup(props, { emit }) {
    const isLogin = ref(true);
    const submitting = ref(false);
    const error = ref('');
    const form = reactive({ username: '', email: '', password: '' });

    async function submit() {
      if (!form.username || !form.password) { error.value = '请填写完整信息'; return; }
      submitting.value = true; error.value = '';
      try {
        const data = isLogin.value
          ? await login({ username: form.username, password: form.password })
          : await register({ username: form.username, email: form.email || undefined, password: form.password });
        store.currentUser = data;
        localStorage.setItem('user', JSON.stringify(data));
        emit('navigate', 'home');
      } catch (e) { error.value = e.message; }
      finally { submitting.value = false; }
    }

    return { isLogin, submitting, error, form, submit };
  },
};

// ── Chat Page (Left-Right Layout) ──
const ChatPage = {
  template: `
    <div class="chat-page">
      <div v-if="!store.currentUser" class="state-msg">
        <div class="icon">🔒</div><h3>请先登录</h3>
      </div>
      <div v-else class="chat-layout">
        <!-- Left: Contact List -->
        <div class="chat-sidebar">
          <div class="chat-sidebar-title">消息</div>
          <div v-if="loadingContacts" style="padding:20px;text-align:center"><div class="spinner"></div></div>
          <template v-else-if="contacts.length === 0">
            <div class="chat-empty-contacts">暂无对话</div>
          </template>
          <div v-for="c in contacts" :key="c.id" class="chat-contact"
            :class="{ active: activeContact?.id === c.id }" @click="selectContact(c)">
            <div class="chat-contact-avatar" :style="{ background: c.color }">{{ c.username[0].toUpperCase() }}</div>
            <div class="chat-contact-info">
              <div class="chat-contact-name">{{ c.username }}</div>
              <div class="chat-contact-preview">{{ c.lastMsg }}</div>
            </div>
          </div>
        </div>
        <!-- Right: Chat Area -->
        <div class="chat-main-area">
          <template v-if="activeContact">
            <div class="chat-main-header">与 {{ activeContact.username }} 的对话</div>
            <div class="chat-msgs" ref="msgBox">
              <div v-if="loadingMsgs" class="chat-loading"><div class="spinner"></div></div>
              <template v-else>
                <div v-for="m in messages" :key="m.id" class="msg"
                  :class="m.sender_id === store.currentUser.id ? 'sent' : 'received'">
                  <div class="msg-content">{{ m.content }}</div>
                  <div class="msg-time">{{ formatDate(m.created_at) }}</div>
                </div>
                <div v-if="messages.length === 0" class="chat-empty-msg">开始对话吧</div>
              </template>
            </div>
            <div class="chat-input-area">
              <input v-model="newMsg" @keyup.enter="send" placeholder="输入消息..." ref="msgInput">
              <button class="btn btn-primary" @click="send" :disabled="!newMsg.trim()">发送</button>
            </div>
          </template>
          <div v-else class="chat-empty-state">
            <div class="chat-empty-icon">💬</div>
            <h3>选择一个联系人开始聊天</h3>
          </div>
        </div>
      </div>
    </div>
  `,
  emits: ['navigate'],
  setup(props, { emit }) {
    const contacts = ref([]);
    const activeContact = ref(null);
    const messages = ref([]);
    const newMsg = ref('');
    const loadingMsgs = ref(false);
    const loadingContacts = ref(true);
    const msgBox = ref(null);
    const msgInput = ref(null);
    let pollTimer = null;

    const avatarColors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4'];

    function getColor(str) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
      return avatarColors[Math.abs(hash) % avatarColors.length];
    }

    async function loadContacts() {
      loadingContacts.value = true;
      try {
        const msgs = await fetchMessages(store.currentUser.id);
        const contactMap = {};
        msgs.forEach(m => {
          const otherId = m.sender_id === store.currentUser.id ? m.receiver_id : m.sender_id;
          const otherName = m.sender_id === store.currentUser.id ? m.receiver_name : m.sender_name;
          if (!contactMap[otherId]) {
            contactMap[otherId] = { id: otherId, username: otherName, lastMsg: '', color: getColor(otherName || '') };
          }
          if (m.content) contactMap[otherId].lastMsg = m.content;
        });
        contacts.value = Object.values(contactMap);
        if (contacts.value.length > 0 && !activeContact.value) {
          selectContact(contacts.value[0]);
        }
      } catch (e) { /* ignore */ }
      finally { loadingContacts.value = false; }
    }

    async function selectContact(contact) {
      activeContact.value = contact;
      loadingMsgs.value = true;
      try {
        const msgs = await fetchMessages(store.currentUser.id, contact.id);
        messages.value = msgs;
        Vue.nextTick(scrollDown);
      } finally { loadingMsgs.value = false; }
    }

    async function send() {
      if (!newMsg.value.trim() || !activeContact.value) return;
      try {
        await sendMsg({
          sender_id: store.currentUser.id,
          receiver_id: activeContact.value.id,
          item_id: store.currentItemId || null,
          content: newMsg.value,
        });
        newMsg.value = '';
        const msgs = await fetchMessages(store.currentUser.id, activeContact.value.id);
        messages.value = msgs;
        Vue.nextTick(scrollDown);
      } catch (e) { alert(e.message); }
    }

    function scrollDown() {
      if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight;
    }

    function startPolling() {
      pollTimer = setInterval(async () => {
        if (store.currentUser) {
          try {
            const uc = await fetchUnreadCount(store.currentUser.id);
            store.unreadCount = uc.count;
          } catch (e) { /* ignore */ }
        }
      }, 5000);
    }

    onMounted(async () => {
      await loadContacts();
      if (store.currentItemId) {
        try {
          const item = await fetchItem(store.currentItemId);
          if (item && item.seller_id !== store.currentUser.id) {
            let contact = contacts.value.find(c => c.id === item.seller_id);
            if (!contact) {
              contact = { id: item.seller_id, username: item.seller_name, lastMsg: '', color: getColor(item.seller_name || '') };
              contacts.value.unshift(contact);
            }
            selectContact(contact);
          }
        } catch (e) { /* ignore */ }
      }
      startPolling();
    });

    onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });

    return { contacts, activeContact, messages, newMsg, loadingMsgs, loadingContacts,
      msgBox, msgInput, store, selectContact, send, formatDate };
  },
};

// ── Orders Page ──
const OrdersPage = {
  template: `
    <div>
      <h2 class="mb-4">我的订单</h2>
      <div style="display:flex;gap:8px;margin-bottom:16px">
        <button class="btn" :class="asBuyer ? 'btn-primary' : 'btn-outline'" @click="asBuyer=true;loadOrders()">作为买家</button>
        <button class="btn" :class="!asBuyer ? 'btn-primary' : 'btn-outline'" @click="asBuyer=false;loadOrders()">作为卖家</button>
      </div>
      <div class="state-msg" v-if="loading"><div class="spinner"></div><h3>加载中...</h3></div>
      <div class="state-msg" v-else-if="orders.length === 0">
        <div class="icon">📋</div><h3>暂无订单</h3>
      </div>
      <div v-else>
        <div class="order-card" v-for="order in orders" :key="order.id">
          <div class="order-info">
            <h4>{{ order.item_title || '物品 #' + order.item_id }}</h4>
            <div class="meta">
              买家: {{ order.buyer_name }} ·
              状态: <strong>{{ statusLabel(order.status) }}</strong> ·
              {{ formatDate(order.created_at) }}
            </div>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <button class="btn btn-sm btn-success" @click="update(order, 'completed')"
              v-if="!asBuyer && order.status === 'pending'">确认完成</button>
            <button class="btn btn-sm btn-danger" @click="update(order, 'cancelled')"
              v-if="!asBuyer && order.status === 'pending'">拒绝</button>
            <span v-if="order.status === 'completed'" style="color:#27ae60;font-weight:500">✅ 已完成</span>
            <span v-if="order.status === 'cancelled'" style="color:#e74c3c">❌ 已取消</span>
          </div>
        </div>
      </div>
    </div>
  `,
  emits: ['navigate'],
  setup(props, { emit }) {
    const orders = ref([]);
    const loading = ref(true);
    const asBuyer = ref(true);

    async function loadOrders() {
      loading.value = true;
      try {
        orders.value = await fetchOrders(store.currentUser.id, asBuyer.value);
      } catch (e) { alert(e.message); }
      finally { loading.value = false; }
    }

    async function update(order, status) {
      try {
        await updateOrder(order.id, { status });
        loadOrders();
      } catch (e) { alert(e.message); }
    }

    onMounted(loadOrders);
    return { orders, loading, asBuyer, loadOrders, update, statusLabel, formatDate };
  },
};

// ── Admin Page ──
const AdminPage = {
  template: `
    <div v-if="!store.currentUser || store.currentUser.role !== 'admin'">
      <div class="state-msg"><div class="icon">🔒</div><h3>需要管理员权限</h3></div>
    </div>
    <div v-else>
      <h2 class="mb-4">管理面板</h2>
      <!-- Stats -->
      <div class="stats-grid">
        <div class="stat-card"><h3>{{ stats.total_items }}</h3><p>物品总数</p></div>
        <div class="stat-card"><h3>{{ stats.total_users }}</h3><p>用户总数</p></div>
        <div class="stat-card"><h3>{{ stats.total_categories }}</h3><p>分类数</p></div>
        <div class="stat-card"><h3>¥{{ stats.avg_price }}</h3><p>平均价格</p></div>
      </div>

      <!-- Batch Update -->
      <div class="admin-panel mb-4">
        <h3 class="mb-4">批量修改物品状态</h3>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <select class="form-control" v-model.number="batchCategory" style="width:160px">
            <option value="">全部分类</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
          </select>
          <select class="form-control" v-model="batchStatus" style="width:120px">
            <option value="active">在售</option>
            <option value="reserved">已预定</option>
            <option value="sold">已售出</option>
          </select>
          <button class="btn btn-warning" @click="batchUpdate">批量修改</button>
          <button class="btn btn-outline" @click="exportCSV">导出CSV</button>
        </div>
      </div>

      <!-- All Items Management -->
      <div class="admin-panel">
        <div class="flex-between mb-4"><h3>所有物品管理</h3></div>
        <div style="overflow-x:auto">
          <table style="width:100%;border-collapse:collapse;font-size:.85rem">
            <thead><tr style="background:#f8f9fa">
              <th style="padding:10px;text-align:left">ID</th>
              <th style="padding:10px;text-align:left">标题</th>
              <th style="padding:10px;text-align:left">价格</th>
              <th style="padding:10px;text-align:left">卖家</th>
              <th style="padding:10px;text-align:left">状态</th>
              <th style="padding:10px;text-align:left">浏览量</th>
              <th style="padding:10px;text-align:left">操作</th>
            </tr></thead>
            <tbody>
              <tr v-for="item in allItems" :key="item.id" style="border-bottom:1px solid #eee">
                <td style="padding:10px">{{ item.id }}</td>
                <td style="padding:10px;max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ item.title }}</td>
                <td style="padding:10px">¥{{ item.price.toFixed(2) }}</td>
                <td style="padding:10px">{{ item.seller_name }}</td>
                <td style="padding:10px"><span class="detail-status" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span></td>
                <td style="padding:10px">{{ item.view_count }}</td>
                <td style="padding:10px">
                  <button class="btn btn-sm btn-danger" @click="adminDelete(item)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PaginationWidget :page="adminPage" :total-pages="adminTotalPages" @page-change="loadAllItems" />
      </div>
    </div>
  `,
  components: { PaginationWidget },
  emits: ['navigate'],
  setup(props, { emit }) {
    const stats = reactive({ total_items: 0, total_users: 0, total_categories: 0, avg_price: 0 });
    const categories = ref([]);
    const allItems = ref([]);
    const adminPage = ref(1);
    const adminTotalPages = ref(1);
    const batchCategory = ref('');
    const batchStatus = ref('active');

    async function loadStats() {
      try { Object.assign(stats, await fetchStats()); } catch (e) { /* ignore */ }
    }
    async function loadAllItems(p) {
      adminPage.value = p || 1;
      try {
        const data = await fetchItems({ page: adminPage.value, page_size: 20 });
        allItems.value = data.items;
        adminTotalPages.value = data.total_pages;
      } catch (e) { /* ignore */ }
    }
    async function batchUpdate() {
      const ids = allItems.value
        .filter(i => !batchCategory.value || i.category_id === batchCategory.value)
        .map(i => i.id);
      if (!ids.length || !confirm(`将 ${ids.length} 个物品状态改为「${statusLabel(batchStatus.value)}」？`)) return;
      try {
        await api('/api/items/batch-update', {
          method: 'POST',
          body: JSON.stringify({ item_ids: ids, status: batchStatus.value }),
        });
        alert('批量修改成功');
        loadAllItems(adminPage.value);
      } catch (e) { alert(e.message); }
    }
    async function exportCSV() {
      window.open(API_BASE + '/api/items/export', '_blank');
    }
    async function adminDelete(item) {
      if (!confirm(`确认删除物品「${item.title}」(ID:${item.id})？`)) return;
      try { await deleteItemApi(item.id, store.currentUser.id); loadAllItems(adminPage.value); }
      catch (e) { alert(e.message); }
    }

    onMounted(() => {
      loadStats();
      loadAllItems(1);
      fetchCategories().then(c => categories.value = c);
    });

    return { stats, categories, allItems, adminPage, adminTotalPages, batchCategory, batchStatus,
      loadAllItems, batchUpdate, exportCSV, adminDelete, store, statusLabel, statusClass, API_BASE };
  },
};


// ══════════════════════════════════════════════
//  Root App
// ══════════════════════════════════════════════

const app = createApp({
  setup() {
    const navOpen = ref(false);

    function goHome() { store.currentPage = 'home'; store.navOpen = false; }
    function goPublish() {
      store.editItemId = null;
      store.currentPage = 'publish';
      store.navOpen = false;
    }
    function goPage(p) {
      store.currentPage = p;
      store.navOpen = false;
    }
    function onNavigate(page, params) {
      store.currentPage = page;
      if (params) Object.assign(store, params);
    }

    function logout() {
      store.currentUser = null;
      localStorage.removeItem('user');
      store.favoritesSet = new Set();
      store.currentPage = 'home';
    }

    // Poll unread count
    let pollTimer = null;
    onMounted(() => {
      pollTimer = setInterval(async () => {
        if (store.currentUser) {
          try {
            const uc = await fetchUnreadCount(store.currentUser.id);
            store.unreadCount = uc.count;
          } catch (e) { /* ignore */ }
        }
      }, 10000);
    });
    onUnmounted(() => { if (pollTimer) clearInterval(pollTimer); });

    return {
      store, logout, goHome, goPublish, goPage, onNavigate, navOpen,
    };
  },
  computed: {
    currentUser() { return store.currentUser; },
    isAdmin() { return store.currentUser?.role === 'admin'; },
    unreadCount() { return store.unreadCount; },
    currentComponent() {
      const map = {
        home: HomePage, detail: ItemDetail, publish: ItemForm,
        'my-items': MyItemsPage, favorites: FavoritesPage,
        login: LoginPage, chat: ChatPage, orders: OrdersPage,
        admin: AdminPage, profile: ProfilePage,
      };
      return map[store.currentPage] || HomePage;
    },
  },
});

app.component('PaginationWidget', PaginationWidget);
app.component('ItemCard', ItemCard);
app.component('ReviewCard', ReviewCard);

app.mount('#app');
