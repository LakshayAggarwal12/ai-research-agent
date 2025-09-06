document.addEventListener('DOMContentLoaded', function() {
    // Form submission handling
    const searchForm = document.getElementById('searchForm');
    const submitText = document.getElementById('submitText');
    const loadingSpinner = document.getElementById('loadingSpinner');
    
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            submitText.textContent = 'Researching...';
            loadingSpinner.classList.remove('d-none');
        });
    }

    // Example search pills
    const examplePills = document.querySelectorAll('.example-pill');
    examplePills.forEach(pill => {
        pill.addEventListener('click', function(e) {
            e.preventDefault();
            const query = this.getAttribute('data-query');
            document.getElementById('query').value = query;
        });
    });

    // Copy link functionality
    const copyButtons = document.querySelectorAll('.copy-link');
    copyButtons.forEach(button => {
        button.addEventListener('click', function() {
            const url = this.getAttribute('data-url');
            navigator.clipboard.writeText(url).then(() => {
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                setTimeout(() => {
                    this.innerHTML = originalText;
                }, 2000);
            });
        });
    });

    // Export functionality
    const exportJson = document.getElementById('exportJson');
    const exportText = document.getElementById('exportText');
    
    if (exportJson) {
        exportJson.addEventListener('click', function() {
            exportResults('json');
        });
    }
    
    if (exportText) {
        exportText.addEventListener('click', function() {
            exportResults('text');
        });
    }

    // Show results after page loads (for results page)
    const resultsSection = document.getElementById('resultsSection');
    const loadingSection = document.getElementById('loadingSection');
    
    if (resultsSection && loadingSection) {
        setTimeout(() => {
            loadingSection.style.display = 'none';
            resultsSection.style.display = 'block';
            resultsSection.classList.add('fade-in');
        }, 2000);
    }

    // Initialize particles background
    initParticles();
});

function exportResults(format) {
    // This would typically make an API call to get export data
    alert(`Exporting results as ${format.toUpperCase()} format...`);
    // Implement actual export logic here
}

function initParticles() {
    const container = document.getElementById('particles');
    if (!container) return;

    // Simple CSS particles effect
    for (let i = 0; i < 30; i++) {
        const particle = document.createElement('div');
        particle.className = 'particle';
        particle.style.cssText = `
            position: absolute;
            width: ${Math.random() * 6 + 2}px;
            height: ${Math.random() * 6 + 2}px;
            background: rgba(255, 255, 255, ${Math.random() * 0.6 + 0.2});
            border-radius: 50%;
            top: ${Math.random() * 100}%;
            left: ${Math.random() * 100}%;
            animation: floatParticle ${Math.random() * 10 + 10}s infinite ease-in-out;
            animation-delay: -${Math.random() * 10}s;
        `;
        container.appendChild(particle);
    }

    // Add CSS for particle animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes floatParticle {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            25% { transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px) rotate(90deg); }
            50% { transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px) rotate(180deg); }
            75% { transform: translate(${Math.random() * 100 - 50}px, ${Math.random() * 100 - 50}px) rotate(270deg); }
        }
        
        .particles-container {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            pointer-events: none;
        }
    `;
    document.head.appendChild(style);
}

// Add some interactive effects
document.addEventListener('DOMContentLoaded', function() {
    // Add hover effects to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 15px 40px rgba(0, 0, 0, 0.15)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.08)';
        });
    });

    // Add typing effect to hero title
    const heroTitle = document.querySelector('.hero-title');
    if (heroTitle) {
        const text = heroTitle.textContent;
        heroTitle.textContent = '';
        let i = 0;
        
        function typeWriter() {
            if (i < text.length) {
                heroTitle.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 50);
            }
        }
        
        setTimeout(typeWriter, 1000);
    }
});