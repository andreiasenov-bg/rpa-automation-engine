// UX Patch: Breadcrumb navigation + Open buttons + clickable rows
(function boot() {
  // Wait for React to mount
  if (!document.querySelector('main')) {
    setTimeout(boot, 200);
    return;
  }

  const LABELS = {
    workflows:'Workflows', executions:'Executions', triggers:'Triggers',
    schedules:'Schedules', credentials:'Credentials', users:'Users',
    settings:'Settings', templates:'Templates', create:'AI Creator',
    agents:'Agents', notifications:'Notifications', 'audit-log':'Audit Log',
    admin:'Admin', plugins:'Plugins', integrations:'Integrations',
    'api-docs':'API Docs', edit:'Editor', files:'Dashboard'
  };

  function svg(d, sz) {
    var s = document.createElementNS('http://www.w3.org/2000/svg','svg');
    s.setAttribute('width',sz);s.setAttribute('height',sz);
    s.setAttribute('viewBox','0 0 24 24');s.setAttribute('fill','none');
    s.setAttribute('stroke','currentColor');s.setAttribute('stroke-width','2');
    s.setAttribute('stroke-linecap','round');s.setAttribute('stroke-linejoin','round');
    s.innerHTML = d; return s;
  }

  function createBC() {
    var old = document.getElementById('ux-bc');
    if (old) old.remove();
    var segs = location.pathname.split('/').filter(Boolean);
    if (!segs.length) return;
    var nav = document.createElement('nav');
    nav.id = 'ux-bc';
    nav.style.cssText = 'display:flex;align-items:center;gap:6px;font-size:13px;margin-bottom:12px;';
    var h = document.createElement('a'); h.href = '/';
    h.style.cssText = 'color:#94a3b8;display:flex;align-items:center;text-decoration:none;';
    h.appendChild(svg('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',14));
    h.onmouseenter = function(){h.style.color='#4f46e5';};
    h.onmouseleave = function(){h.style.color='#94a3b8';};
    nav.appendChild(h);
    var crumbs = [];
    for (var i = 0; i < segs.length; i++) {
      var seg = segs[i], p = '/' + segs.slice(0,i+1).join('/');
      if (/^[0-9a-f]{8}-/.test(seg)) {
        var el = document.querySelector('.text-xl,.text-2xl,h1,h2');
        var nm = el ? el.textContent.trim() : 'Workflow';
        if (nm.length > 42) nm = nm.substring(0,39) + '...';
        crumbs.push({label:nm, path:'/workflows/'+seg+'/files'});
        continue;
      }
      crumbs.push({label: LABELS[seg] || seg.charAt(0).toUpperCase()+seg.slice(1), path:p});
    }
    crumbs.forEach(function(c, i) {
      var sep = document.createElement('span');
      sep.textContent = '\u203A'; sep.style.cssText = 'color:#cbd5e1;font-size:16px;';
      nav.appendChild(sep);
      if (i === crumbs.length - 1) {
        var s = document.createElement('span');
        s.textContent = c.label; s.style.cssText = 'font-weight:600;color:#334155;';
        nav.appendChild(s);
      } else {
        var a = document.createElement('a'); a.href = c.path; a.textContent = c.label;
        a.style.cssText = 'color:#94a3b8;text-decoration:none;';
        a.onmouseenter = function(){this.style.color='#4f46e5';};
        a.onmouseleave = function(){this.style.color='#94a3b8';};
        nav.appendChild(a);
      }
    });
    var mc = document.querySelector('main .p-6');
    if (mc && mc.firstChild) mc.insertBefore(nav, mc.firstChild);
  }

  function patchWfList() {
    document.querySelectorAll('table tbody tr').forEach(function(row) {
      var nl = row.querySelector('td:first-child a');
      if (!nl) return;
      if (nl.href.includes('/edit')) nl.href = nl.href.replace('/edit','/files');
      row.style.cursor = 'pointer';
      if (!row.dataset.ux) {
        row.dataset.ux = '1';
        row.addEventListener('click', function(e) {
          if (e.target.closest('td:last-child')) return;
          nl.click();
        });
      }
      var ac = row.querySelector('td:last-child div');
      if (ac && !ac.querySelector('.ux-open')) {
        var wfId = (nl.href.match(/workflows\/([^/]+)/) || [])[1] || '';
        var btn = document.createElement('a');
        btn.href = '/workflows/' + wfId + '/files';
        btn.className = 'ux-open';
        btn.style.cssText = 'display:inline-flex;align-items:center;gap:4px;padding:4px 10px;font-size:12px;font-weight:500;background:#f1f5f9;color:#475569;border-radius:8px;text-decoration:none;margin-right:4px;';
        btn.onmouseenter = function(){btn.style.background='#eef2ff';btn.style.color='#4f46e5';};
        btn.onmouseleave = function(){btn.style.background='#f1f5f9';btn.style.color='#475569';};
        btn.appendChild(svg('<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',12));
        btn.appendChild(document.createTextNode(' Open'));
        ac.insertBefore(btn, ac.firstChild);
      }
    });
  }

  function applyAll() { createBC(); patchWfList(); }

  applyAll();

  var lastUrl = location.href;
  var obs = new MutationObserver(function() {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      [200,600,1500,3000].forEach(function(d){ setTimeout(applyAll, d); });
    }
    if (!document.getElementById('ux-bc') && location.pathname !== '/') {
      setTimeout(applyAll, 150);
    }
  });
  obs.observe(document.body, {childList:true, subtree:true});
})();
