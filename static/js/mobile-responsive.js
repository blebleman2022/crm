/**
 * CRM系统移动端响应式JavaScript功能
 */

// 移动端检测
const isMobile = () => window.innerWidth <= 768;
const isTablet = () => window.innerWidth > 768 && window.innerWidth <= 1024;
const isDesktop = () => window.innerWidth > 1024;

// 移动端侧边栏控制
class MobileSidebar {
    constructor() {
        this.overlay = null;
        this.sidebar = null;
        this.isOpen = false;
        this.init();
    }

    init() {
        this.createOverlay();
        this.bindEvents();
        this.handleResize();
    }

    createOverlay() {
        // 创建遮罩层
        this.overlay = document.createElement('div');
        this.overlay.className = 'mobile-nav-overlay hidden';
        this.overlay.id = 'sidebar-overlay';
        document.body.appendChild(this.overlay);

        // 点击遮罩关闭侧边栏
        this.overlay.addEventListener('click', () => this.close());
    }

    bindEvents() {
        // 绑定菜单按钮事件
        const menuButtons = document.querySelectorAll('[data-mobile-menu]');
        menuButtons.forEach(button => {
            button.addEventListener('click', () => this.toggle());
        });

        // 监听窗口大小变化
        window.addEventListener('resize', () => this.handleResize());

        // ESC键关闭侧边栏
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.overlay.classList.remove('hidden');
        
        // 查找侧边栏元素
        const sidebar = document.querySelector('.sidebar, aside, [data-sidebar]');
        if (sidebar) {
            sidebar.classList.add('mobile-sidebar', 'open');
        }
        
        // 防止背景滚动
        document.body.style.overflow = 'hidden';
    }

    close() {
        this.isOpen = false;
        this.overlay.classList.add('hidden');
        
        const sidebar = document.querySelector('.mobile-sidebar');
        if (sidebar) {
            sidebar.classList.remove('open');
        }
        
        // 恢复背景滚动
        document.body.style.overflow = '';
    }

    handleResize() {
        if (!isMobile() && this.isOpen) {
            this.close();
        }
    }
}

// 移动端表格转换
class MobileTable {
    constructor() {
        this.init();
    }

    init() {
        this.convertTables();
        // 初始化时立即检查设备类型
        this.handleResize();
        window.addEventListener('resize', () => this.handleResize());
    }

    convertTables() {
        if (!isMobile()) return;

        const tables = document.querySelectorAll('table:not(.no-mobile-convert)');
        tables.forEach(table => this.convertTable(table));
    }

    convertTable(table) {
        if (table.classList.contains('mobile-converted')) return;

        table.classList.add('mobile-table', 'mobile-converted');
        
        // 获取表头
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        
        // 为每个单元格添加data-label属性
        const rows = table.querySelectorAll('tbody tr');
        rows.forEach(row => {
            const cells = row.querySelectorAll('td');
            cells.forEach((cell, index) => {
                if (headers[index]) {
                    cell.setAttribute('data-label', headers[index]);
                }
            });
        });
    }

    handleResize() {
        const tables = document.querySelectorAll('.mobile-converted');
        if (isMobile()) {
            tables.forEach(table => table.classList.add('mobile-table'));
        } else {
            tables.forEach(table => {
                table.classList.remove('mobile-table');
                // 强制重置表格样式
                table.style.display = '';
                const thead = table.querySelector('thead');
                if (thead) thead.style.display = '';
                const tbody = table.querySelector('tbody');
                if (tbody) tbody.style.display = '';
                const rows = table.querySelectorAll('tr');
                rows.forEach(row => {
                    row.style.display = '';
                    row.style.border = '';
                    row.style.marginBottom = '';
                    row.style.padding = '';
                    row.style.background = '';
                    row.style.boxShadow = '';
                });
                const cells = table.querySelectorAll('td, th');
                cells.forEach(cell => {
                    cell.style.display = '';
                    cell.style.border = '';
                    cell.style.padding = '';
                    cell.style.position = '';
                    cell.style.width = '';
                });
            });
        }
    }
}

// 移动端表单优化
class MobileForm {
    constructor() {
        this.init();
    }

    init() {
        this.optimizeForms();
        this.handleInputFocus();
    }

    optimizeForms() {
        if (!isMobile()) return;

        // 为所有表单添加移动端类
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.classList.add('mobile-form');
        });

        // 优化输入框
        const inputs = document.querySelectorAll('input, textarea, select');
        inputs.forEach(input => {
            input.classList.add('form-control');
            
            // 设置合适的输入类型
            if (input.type === 'email') {
                input.setAttribute('inputmode', 'email');
            } else if (input.type === 'tel') {
                input.setAttribute('inputmode', 'tel');
            } else if (input.type === 'number') {
                input.setAttribute('inputmode', 'numeric');
            }
        });
    }

    handleInputFocus() {
        // iOS Safari输入框聚焦时滚动到视图
        const inputs = document.querySelectorAll('input, textarea');
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                if (isMobile()) {
                    setTimeout(() => {
                        input.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }, 300);
                }
            });
        });
    }
}

// 移动端模态框优化
class MobileModal {
    constructor() {
        this.init();
    }

    init() {
        this.optimizeModals();
    }

    optimizeModals() {
        const modals = document.querySelectorAll('.modal, [data-modal]');
        modals.forEach(modal => {
            if (isMobile()) {
                modal.classList.add('mobile-modal');
                
                // 添加关闭按钮
                this.addCloseButton(modal);
            }
        });
    }

    addCloseButton(modal) {
        const closeBtn = modal.querySelector('.modal-close, [data-dismiss="modal"]');
        if (!closeBtn) {
            const newCloseBtn = document.createElement('button');
            newCloseBtn.className = 'modal-close mobile-only';
            newCloseBtn.innerHTML = '<span class="material-symbols-outlined">close</span>';
            newCloseBtn.style.cssText = 'position: absolute; top: 16px; right: 16px; z-index: 10;';
            
            const modalContent = modal.querySelector('.modal-content, .modal-body');
            if (modalContent) {
                modalContent.style.position = 'relative';
                modalContent.appendChild(newCloseBtn);
            }
        }
    }
}

// 移动端搜索优化
class MobileSearch {
    constructor() {
        this.init();
    }

    init() {
        this.optimizeSearchInputs();
    }

    optimizeSearchInputs() {
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input, [data-search]');
        searchInputs.forEach(input => {
            if (isMobile()) {
                // 包装搜索输入框
                this.wrapSearchInput(input);
            }
        });
    }

    wrapSearchInput(input) {
        if (input.parentElement.classList.contains('search-container')) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'search-container';
        
        const icon = document.createElement('span');
        icon.className = 'material-symbols-outlined search-icon';
        icon.textContent = 'search';
        
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(icon);
        wrapper.appendChild(input);
        
        input.classList.add('search-input');
    }
}

// 移动端触摸手势
class MobileGestures {
    constructor() {
        this.init();
    }

    init() {
        this.addSwipeGestures();
        this.addTouchFeedback();
    }

    addSwipeGestures() {
        let startX, startY, endX, endY;

        document.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            startY = e.touches[0].clientY;
        });

        document.addEventListener('touchend', (e) => {
            endX = e.changedTouches[0].clientX;
            endY = e.changedTouches[0].clientY;
            
            this.handleSwipe(startX, startY, endX, endY);
        });
    }

    handleSwipe(startX, startY, endX, endY) {
        const deltaX = endX - startX;
        const deltaY = endY - startY;
        const minSwipeDistance = 50;

        // 水平滑动
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > minSwipeDistance) {
            if (deltaX > 0) {
                // 向右滑动 - 打开侧边栏
                if (window.mobileSidebar && !window.mobileSidebar.isOpen) {
                    window.mobileSidebar.open();
                }
            } else {
                // 向左滑动 - 关闭侧边栏
                if (window.mobileSidebar && window.mobileSidebar.isOpen) {
                    window.mobileSidebar.close();
                }
            }
        }
    }

    addTouchFeedback() {
        const touchElements = document.querySelectorAll('button, .btn, a, [data-touch]');
        touchElements.forEach(element => {
            element.classList.add('touch-target');
            
            element.addEventListener('touchstart', () => {
                element.style.opacity = '0.7';
            });
            
            element.addEventListener('touchend', () => {
                setTimeout(() => {
                    element.style.opacity = '';
                }, 150);
            });
        });
    }
}

// 移动端性能优化
class MobilePerformance {
    constructor() {
        this.init();
    }

    init() {
        this.lazyLoadImages();
        this.optimizeAnimations();
    }

    lazyLoadImages() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    imageObserver.unobserve(img);
                }
            });
        });

        images.forEach(img => imageObserver.observe(img));
    }

    optimizeAnimations() {
        // 在移动设备上减少动画
        if (isMobile()) {
            const style = document.createElement('style');
            style.textContent = `
                *, *::before, *::after {
                    animation-duration: 0.01ms !important;
                    animation-iteration-count: 1 !important;
                    transition-duration: 0.01ms !important;
                }
            `;
            document.head.appendChild(style);
        }
    }
}

// 初始化所有移动端功能
document.addEventListener('DOMContentLoaded', () => {
    // 只在移动设备上初始化
    if (isMobile() || isTablet()) {
        window.mobileSidebar = new MobileSidebar();
        window.mobileTable = new MobileTable();
        window.mobileForm = new MobileForm();
        window.mobileModal = new MobileModal();
        window.mobileSearch = new MobileSearch();
        window.mobileGestures = new MobileGestures();
        window.mobilePerformance = new MobilePerformance();
        
        console.log('移动端功能已初始化');
    }
});

// 导出工具函数
window.MobileUtils = {
    isMobile,
    isTablet,
    isDesktop,
    
    // 显示移动端提示
    showMobileToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `mobile-toast mobile-toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            z-index: 1000;
            font-size: 14px;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    },
    
    // 滚动到顶部
    scrollToTop() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
};
