/**
 * MINDMED Wellbeing Assessment Script
 */

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('assessmentForm');
  const progressBar = document.getElementById('assessmentProgress');
  const progressText = document.getElementById('progressText');

  if (!form) return;

  const radioGroups = [
    'mood', 'stress', 'energy', 'sleep',
    'anx_nervous', 'anx_worry',
    'dep_pleasure', 'dep_hopeless',
    'burn_exhaustion', 'burn_motivation', 'burn_recovery',
    'hlth_fatigue', 'hlth_activity'
  ];

  function updateProgress() {
    let answered = 0;
    radioGroups.forEach(name => {
      const selected = form.querySelector(`input[name="${name}"]:checked`);
      if (selected) {
        answered++;
      }
    });

    const percent = Math.round((answered / radioGroups.length) * 100);
    if (progressBar) {
      progressBar.style.width = `${percent}%`;
    }
    if (progressText) {
      progressText.textContent = `${answered} of ${radioGroups.length} questions answered (${percent}%)`;
    }
  }

  // Listen to changes on radio buttons
  form.querySelectorAll('input[type="radio"]').forEach(radio => {
    radio.addEventListener('change', updateProgress);
  });

  // Form submission check
  form.addEventListener('submit', (e) => {
    let missing = [];
    radioGroups.forEach(name => {
      const selected = form.querySelector(`input[name="${name}"]:checked`);
      if (!selected) {
        missing.push(name);
      }
    });

    if (missing.length > 0) {
      e.preventDefault();
      alert('Please answer all questions before submitting your wellbeing check.');
      // Scroll to first unanswered question
      const firstMissing = form.querySelector(`input[name="${missing[0]}"]`);
      if (firstMissing) {
        firstMissing.closest('.question-block').scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }
  });

  // Initial calculation
  updateProgress();
});
