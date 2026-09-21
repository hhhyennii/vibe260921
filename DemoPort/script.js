(() => {
  const root = document.documentElement;
  const themeToggle = document.getElementById('themeToggle');
  const navToggle = document.getElementById('navToggle');
  const mainNav = document.getElementById('mainNav');
  const navLinks = document.querySelectorAll('.nav-link');
  const sections = document.querySelectorAll('main .section[id]');

  // 다크모드
  const savedTheme = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
    root.setAttribute('data-theme', 'dark');
  }

  themeToggle.addEventListener('click', () => {
    const isDark = root.getAttribute('data-theme') === 'dark';
    if (isDark) {
      root.removeAttribute('data-theme');
      localStorage.setItem('theme', 'light');
    } else {
      root.setAttribute('data-theme', 'dark');
      localStorage.setItem('theme', 'dark');
    }
  });

  // 모바일 메뉴
  navToggle.addEventListener('click', () => {
    const isOpen = mainNav.classList.toggle('open');
    navToggle.setAttribute('aria-expanded', String(isOpen));
  });

  navLinks.forEach((link) => {
    link.addEventListener('click', () => {
      mainNav.classList.remove('open');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });

  // 스크롤 위치에 따른 활성 메뉴 표시
  const setActiveLink = () => {
    let current = sections[0]?.id;
    const scrollPos = window.scrollY + 120;
    sections.forEach((section) => {
      if (section.offsetTop <= scrollPos) {
        current = section.id;
      }
    });
    navLinks.forEach((link) => {
      link.classList.toggle('active', link.getAttribute('href') === `#${current}`);
    });
  };

  window.addEventListener('scroll', setActiveLink, { passive: true });
  setActiveLink();

  // 카드 등장 애니메이션
  const revealEls = document.querySelectorAll('.reveal');
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('in-view');
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.15 }
  );
  revealEls.forEach((el) => observer.observe(el));
})();
