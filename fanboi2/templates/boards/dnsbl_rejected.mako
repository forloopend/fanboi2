<%inherit file="../partials/_layout.mako" />
<%include file="_header.mako" />
<%def name="title()">${board.title}</%def>
<div class="item-error">
    <div class="container">
        <h2 class="title">Post rejected.</h2>
        <p class="description">Your IP is blacklisted with DNSBL and therefore rejected.</p>
    </div>
</div>
