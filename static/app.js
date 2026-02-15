const form = document.getElementById('search-form');
const statusEl = document.getElementById('status');
const resultsEl = document.getElementById('results');

function selectedCategories() {
  return Array.from(document.querySelectorAll('.categories input[type="checkbox"]'))
    .filter((el) => el.checked)
    .map((el) => el.value);
}

function scoreBadge(score) {
  if (score >= 5) return '🔥 very hot';
  if (score >= 3.5) return '⭐ popular';
  return '👍 solid';
}

async function runSearch() {
  const query = document.getElementById('query').value.trim();
  const city = document.getElementById('city').value;
  const categories = selectedCategories();

  if (!query) return;
  if (!categories.length) {
    statusEl.textContent = 'Please select at least one category.';
    return;
  }

  statusEl.textContent = 'Searching Korean Naver blogs and ranking popular spots...';
  resultsEl.innerHTML = '';

  const url = `/api/search?q=${encodeURIComponent(query)}&city=${encodeURIComponent(city)}&categories=${encodeURIComponent(categories.join(','))}&limit=20`;

  try {
    const response = await fetch(url);
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || 'Search failed');
    }

    statusEl.textContent = `${data.city.toUpperCase()} • Korean search: ${data.queries_ko.join(' | ')} • ${data.count} ranked results`;

    if (!data.items.length) {
      resultsEl.innerHTML = '<p>No results found.</p>';
      return;
    }

    resultsEl.innerHTML = data.items
      .map(
        (item, i) => `
      <article class="card">
        <div class="rank">#${i + 1} ${scoreBadge(item.popularity_score)} · score ${item.popularity_score}</div>
        <h3>${item.place_name_en || item.title_en}</h3>
        <p class="korean">${item.place_name_ko || item.title_ko}</p>
        <p>${item.description_en || ''}</p>
        <div class="meta">Neighborhood: ${item.neighborhood_en || item.neighborhood_ko || 'N/A'} · Mentions: ${item.mention_count}</div>
        <div class="links">
          <a href="${item.blog_link}" target="_blank" rel="noopener noreferrer">Open Naver blog</a>
          <a href="${item.map_link}" target="_blank" rel="noopener noreferrer">Open map</a>
        </div>
      </article>
    `
      )
      .join('');
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  await runSearch();
});

// quick default query so it feels immediate
window.addEventListener('load', async () => {
  document.getElementById('query').value = 'popular local spots';
  await runSearch();
});
