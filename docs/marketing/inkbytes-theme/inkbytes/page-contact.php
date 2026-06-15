<?php
/**
 * Contact — generated from site/contact.html by build-templates.py.
 * Re-run the script after editing the source HTML, or edit here directly.
 *
 * @package InkBytes
 */
if ( ! defined( 'ABSPATH' ) ) { exit; }
get_header();
?>
<main>

  <section class="page-hero page-hero--accent">
    <div class="wrap">
      <span class="kicker"><span class="pulse"></span> Contact</span>
      <h1>Get in <span class="accent">touch</span>.</h1>
      <p class="lead">Questions, corrections, or press — we read everything. No marketing funnels, no dark patterns.</p>
    </div>
  </section>

  <section class="section">
    <div class="wrap">
      <div class="contact-grid">
        <div class="card contact-card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/></svg></span>
          <h3>General</h3>
          <p>For anything about the product, membership, or partnerships.</p>
          <a class="email" href="mailto:hello@inkbytes.news">hello@inkbytes.news</a>
        </div>
        <div class="card contact-card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></svg></span>
          <h3>Report a correction</h3>
          <p>Spotted an error on an event page? Send the page and what's wrong. We fix it in the open.</p>
          <a class="email" href="mailto:corrections@inkbytes.news">corrections@inkbytes.news</a>
        </div>
        <div class="card contact-card">
          <span class="icon-badge"><svg class="uicon" viewBox="0 0 24 24"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1.5" fill="currentColor" stroke="none"/></svg></span>
          <h3>Press</h3>
          <p>InkBytes is a paid, ad-free news reader that synthesizes one cited page per event. Built in the Dominican Republic.</p>
          <a class="email" href="mailto:press@inkbytes.news">press@inkbytes.news</a>
        </div>
      </div>
    </div>
  </section>

  <section class="section--tight">
    <div class="wrap">
      <div class="sec-head center" style="margin-bottom:32px">
        <span class="kicker">Send a message</span>
        <h2 class="h-sec">Or just write to us here.</h2>
      </div>
      <form class="contact-form" onsubmit="return false">
        <div class="field-row">
          <div class="field">
            <label for="cf-name">Name</label>
            <input id="cf-name" type="text" placeholder="Your name" autocomplete="name" />
          </div>
          <div class="field">
            <label for="cf-email">Email</label>
            <input id="cf-email" type="email" placeholder="you@example.com" autocomplete="email" />
          </div>
        </div>
        <div class="field">
          <label for="cf-topic">Topic</label>
          <select id="cf-topic">
            <option>General question</option>
            <option>Report a correction</option>
            <option>Membership &amp; billing</option>
            <option>Press</option>
          </select>
        </div>
        <div class="field">
          <label for="cf-msg">Message</label>
          <textarea id="cf-msg" placeholder="What's on your mind?"></textarea>
        </div>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:18px;flex-wrap:wrap">
          <p class="form-note"><span class="pulse"></span> We don't add you to any marketing list. Ever.</p>
          <button class="ib-btn v-primary sz-md" type="submit">Send message</button>
        </div>
      </form>
    </div>
  </section>

  <section class="section band center">
    <div class="wrap measure">
      <h2 class="h-sec" style="margin:0 auto 18px">Rather just read?</h2>
      <p class="lead" style="margin:0 auto 30px">Browse every event free in the reader, and see the synthesis for yourself.</p>
      <a class="ib-btn v-primary sz-lg" href="https://inkbytes.org">Start reading — $9/mo</a>
    </div>
  </section>

</main>
<?php
get_footer();
