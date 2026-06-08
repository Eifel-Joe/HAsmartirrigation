!function (e) {
  "use strict";

  var t = function (e, a) {
    return t = Object.setPrototypeOf || {
      __proto__: []
    } instanceof Array && function (e, t) {
      e.__proto__ = t;
    } || function (e, t) {
      for (var a in t) Object.prototype.hasOwnProperty.call(t, a) && (e[a] = t[a]);
    }, t(e, a);
  };
  function a(e, a) {
    if ("function" != typeof a && null !== a) throw new TypeError("Class extends value " + String(a) + " is not a constructor or null");
    function i() {
      this.constructor = e;
    }
    t(e, a), e.prototype = null === a ? Object.create(a) : (i.prototype = a.prototype, new i());
  }
  var i = function () {
    return i = Object.assign || function (e) {
      for (var t, a = 1, i = arguments.length; a < i; a++) for (var n in t = arguments[a]) Object.prototype.hasOwnProperty.call(t, n) && (e[n] = t[n]);
      return e;
    }, i.apply(this, arguments);
  };
  function n(e, t, a, i) {
    var n,
      r = arguments.length,
      o = r < 3 ? t : null === i ? i = Object.getOwnPropertyDescriptor(t, a) : i;
    if ("object" == typeof Reflect && "function" == typeof Reflect.decorate) o = Reflect.decorate(e, t, a, i);else for (var s = e.length - 1; s >= 0; s--) (n = e[s]) && (o = (r < 3 ? n(o) : r > 3 ? n(t, a, o) : n(t, a)) || o);
    return r > 3 && o && Object.defineProperty(t, a, o), o;
  }
  function r(e, t, a) {
    if (a || 2 === arguments.length) for (var i, n = 0, r = t.length; n < r; n++) !i && n in t || (i || (i = Array.prototype.slice.call(t, 0, n)), i[n] = t[n]);
    return e.concat(i || Array.prototype.slice.call(t));
  }
  "function" == typeof SuppressedError && SuppressedError;
  /**
       * @license
       * Copyright 2019 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  const o = window,
    s = o.ShadowRoot && (void 0 === o.ShadyCSS || o.ShadyCSS.nativeShadow) && "adoptedStyleSheets" in Document.prototype && "replace" in CSSStyleSheet.prototype,
    l = Symbol(),
    d = new WeakMap();
  class u {
    constructor(e, t, a) {
      if (this._$cssResult$ = !0, a !== l) throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");
      this.cssText = e, this.t = t;
    }
    get styleSheet() {
      let e = this.o;
      const t = this.t;
      if (s && void 0 === e) {
        const a = void 0 !== t && 1 === t.length;
        a && (e = d.get(t)), void 0 === e && ((this.o = e = new CSSStyleSheet()).replaceSync(this.cssText), a && d.set(t, e));
      }
      return e;
    }
    toString() {
      return this.cssText;
    }
  }
  const c = (e, ...t) => {
      const a = 1 === e.length ? e[0] : t.reduce((t, a, i) => t + (e => {
        if (!0 === e._$cssResult$) return e.cssText;
        if ("number" == typeof e) return e;
        throw Error("Value passed to 'css' function must be a 'css' function result: " + e + ". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.");
      })(a) + e[i + 1], e[0]);
      return new u(a, e, l);
    },
    p = s ? e => e : e => e instanceof CSSStyleSheet ? (e => {
      let t = "";
      for (const a of e.cssRules) t += a.cssText;
      return (e => new u("string" == typeof e ? e : e + "", void 0, l))(t);
    })(e) : e
    /**
         * @license
         * Copyright 2017 Google LLC
         * SPDX-License-Identifier: BSD-3-Clause
         */;
  var m;
  const g = window,
    h = g.trustedTypes,
    v = h ? h.emptyScript : "",
    _ = g.reactiveElementPolyfillSupport,
    b = {
      toAttribute(e, t) {
        switch (t) {
          case Boolean:
            e = e ? v : null;
            break;
          case Object:
          case Array:
            e = null == e ? e : JSON.stringify(e);
        }
        return e;
      },
      fromAttribute(e, t) {
        let a = e;
        switch (t) {
          case Boolean:
            a = null !== e;
            break;
          case Number:
            a = null === e ? null : Number(e);
            break;
          case Object:
          case Array:
            try {
              a = JSON.parse(e);
            } catch (e) {
              a = null;
            }
        }
        return a;
      }
    },
    f = (e, t) => t !== e && (t == t || e == e),
    k = {
      attribute: !0,
      type: String,
      converter: b,
      reflect: !1,
      hasChanged: f
    },
    z = "finalized";
  class y extends HTMLElement {
    constructor() {
      super(), this._$Ei = new Map(), this.isUpdatePending = !1, this.hasUpdated = !1, this._$El = null, this._$Eu();
    }
    static addInitializer(e) {
      var t;
      this.finalize(), (null !== (t = this.h) && void 0 !== t ? t : this.h = []).push(e);
    }
    static get observedAttributes() {
      this.finalize();
      const e = [];
      return this.elementProperties.forEach((t, a) => {
        const i = this._$Ep(a, t);
        void 0 !== i && (this._$Ev.set(i, a), e.push(i));
      }), e;
    }
    static createProperty(e, t = k) {
      if (t.state && (t.attribute = !1), this.finalize(), this.elementProperties.set(e, t), !t.noAccessor && !this.prototype.hasOwnProperty(e)) {
        const a = "symbol" == typeof e ? Symbol() : "__" + e,
          i = this.getPropertyDescriptor(e, a, t);
        void 0 !== i && Object.defineProperty(this.prototype, e, i);
      }
    }
    static getPropertyDescriptor(e, t, a) {
      return {
        get() {
          return this[t];
        },
        set(i) {
          const n = this[e];
          this[t] = i, this.requestUpdate(e, n, a);
        },
        configurable: !0,
        enumerable: !0
      };
    }
    static getPropertyOptions(e) {
      return this.elementProperties.get(e) || k;
    }
    static finalize() {
      if (this.hasOwnProperty(z)) return !1;
      this[z] = !0;
      const e = Object.getPrototypeOf(this);
      if (e.finalize(), void 0 !== e.h && (this.h = [...e.h]), this.elementProperties = new Map(e.elementProperties), this._$Ev = new Map(), this.hasOwnProperty("properties")) {
        const e = this.properties,
          t = [...Object.getOwnPropertyNames(e), ...Object.getOwnPropertySymbols(e)];
        for (const a of t) this.createProperty(a, e[a]);
      }
      return this.elementStyles = this.finalizeStyles(this.styles), !0;
    }
    static finalizeStyles(e) {
      const t = [];
      if (Array.isArray(e)) {
        const a = new Set(e.flat(1 / 0).reverse());
        for (const e of a) t.unshift(p(e));
      } else void 0 !== e && t.push(p(e));
      return t;
    }
    static _$Ep(e, t) {
      const a = t.attribute;
      return !1 === a ? void 0 : "string" == typeof a ? a : "string" == typeof e ? e.toLowerCase() : void 0;
    }
    _$Eu() {
      var e;
      this._$E_ = new Promise(e => this.enableUpdating = e), this._$AL = new Map(), this._$Eg(), this.requestUpdate(), null === (e = this.constructor.h) || void 0 === e || e.forEach(e => e(this));
    }
    addController(e) {
      var t, a;
      (null !== (t = this._$ES) && void 0 !== t ? t : this._$ES = []).push(e), void 0 !== this.renderRoot && this.isConnected && (null === (a = e.hostConnected) || void 0 === a || a.call(e));
    }
    removeController(e) {
      var t;
      null === (t = this._$ES) || void 0 === t || t.splice(this._$ES.indexOf(e) >>> 0, 1);
    }
    _$Eg() {
      this.constructor.elementProperties.forEach((e, t) => {
        this.hasOwnProperty(t) && (this._$Ei.set(t, this[t]), delete this[t]);
      });
    }
    createRenderRoot() {
      var e;
      const t = null !== (e = this.shadowRoot) && void 0 !== e ? e : this.attachShadow(this.constructor.shadowRootOptions);
      return ((e, t) => {
        s ? e.adoptedStyleSheets = t.map(e => e instanceof CSSStyleSheet ? e : e.styleSheet) : t.forEach(t => {
          const a = document.createElement("style"),
            i = o.litNonce;
          void 0 !== i && a.setAttribute("nonce", i), a.textContent = t.cssText, e.appendChild(a);
        });
      })(t, this.constructor.elementStyles), t;
    }
    connectedCallback() {
      var e;
      void 0 === this.renderRoot && (this.renderRoot = this.createRenderRoot()), this.enableUpdating(!0), null === (e = this._$ES) || void 0 === e || e.forEach(e => {
        var t;
        return null === (t = e.hostConnected) || void 0 === t ? void 0 : t.call(e);
      });
    }
    enableUpdating(e) {}
    disconnectedCallback() {
      var e;
      null === (e = this._$ES) || void 0 === e || e.forEach(e => {
        var t;
        return null === (t = e.hostDisconnected) || void 0 === t ? void 0 : t.call(e);
      });
    }
    attributeChangedCallback(e, t, a) {
      this._$AK(e, a);
    }
    _$EO(e, t, a = k) {
      var i;
      const n = this.constructor._$Ep(e, a);
      if (void 0 !== n && !0 === a.reflect) {
        const r = (void 0 !== (null === (i = a.converter) || void 0 === i ? void 0 : i.toAttribute) ? a.converter : b).toAttribute(t, a.type);
        this._$El = e, null == r ? this.removeAttribute(n) : this.setAttribute(n, r), this._$El = null;
      }
    }
    _$AK(e, t) {
      var a;
      const i = this.constructor,
        n = i._$Ev.get(e);
      if (void 0 !== n && this._$El !== n) {
        const e = i.getPropertyOptions(n),
          r = "function" == typeof e.converter ? {
            fromAttribute: e.converter
          } : void 0 !== (null === (a = e.converter) || void 0 === a ? void 0 : a.fromAttribute) ? e.converter : b;
        this._$El = n, this[n] = r.fromAttribute(t, e.type), this._$El = null;
      }
    }
    requestUpdate(e, t, a) {
      let i = !0;
      void 0 !== e && (((a = a || this.constructor.getPropertyOptions(e)).hasChanged || f)(this[e], t) ? (this._$AL.has(e) || this._$AL.set(e, t), !0 === a.reflect && this._$El !== e && (void 0 === this._$EC && (this._$EC = new Map()), this._$EC.set(e, a))) : i = !1), !this.isUpdatePending && i && (this._$E_ = this._$Ej());
    }
    async _$Ej() {
      this.isUpdatePending = !0;
      try {
        await this._$E_;
      } catch (e) {
        Promise.reject(e);
      }
      const e = this.scheduleUpdate();
      return null != e && (await e), !this.isUpdatePending;
    }
    scheduleUpdate() {
      return this.performUpdate();
    }
    performUpdate() {
      var e;
      if (!this.isUpdatePending) return;
      this.hasUpdated, this._$Ei && (this._$Ei.forEach((e, t) => this[t] = e), this._$Ei = void 0);
      let t = !1;
      const a = this._$AL;
      try {
        t = this.shouldUpdate(a), t ? (this.willUpdate(a), null === (e = this._$ES) || void 0 === e || e.forEach(e => {
          var t;
          return null === (t = e.hostUpdate) || void 0 === t ? void 0 : t.call(e);
        }), this.update(a)) : this._$Ek();
      } catch (e) {
        throw t = !1, this._$Ek(), e;
      }
      t && this._$AE(a);
    }
    willUpdate(e) {}
    _$AE(e) {
      var t;
      null === (t = this._$ES) || void 0 === t || t.forEach(e => {
        var t;
        return null === (t = e.hostUpdated) || void 0 === t ? void 0 : t.call(e);
      }), this.hasUpdated || (this.hasUpdated = !0, this.firstUpdated(e)), this.updated(e);
    }
    _$Ek() {
      this._$AL = new Map(), this.isUpdatePending = !1;
    }
    get updateComplete() {
      return this.getUpdateComplete();
    }
    getUpdateComplete() {
      return this._$E_;
    }
    shouldUpdate(e) {
      return !0;
    }
    update(e) {
      void 0 !== this._$EC && (this._$EC.forEach((e, t) => this._$EO(t, this[t], e)), this._$EC = void 0), this._$Ek();
    }
    updated(e) {}
    firstUpdated(e) {}
  }
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  var w;
  y[z] = !0, y.elementProperties = new Map(), y.elementStyles = [], y.shadowRootOptions = {
    mode: "open"
  }, null == _ || _({
    ReactiveElement: y
  }), (null !== (m = g.reactiveElementVersions) && void 0 !== m ? m : g.reactiveElementVersions = []).push("1.6.3");
  const A = window,
    S = A.trustedTypes,
    E = S ? S.createPolicy("lit-html", {
      createHTML: e => e
    }) : void 0,
    x = "$lit$",
    T = `lit$${(Math.random() + "").slice(9)}$`,
    j = "?" + T,
    P = `<${j}>`,
    M = document,
    D = () => M.createComment(""),
    C = e => null === e || "object" != typeof e && "function" != typeof e,
    H = Array.isArray,
    L = "[ \t\n\f\r]",
    B = /<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,
    N = /-->/g,
    I = />/g,
    O = RegExp(`>|${L}(?:([^\\s"'>=/]+)(${L}*=${L}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`, "g"),
    $ = /'/g,
    R = /"/g,
    V = /^(?:script|style|textarea|title)$/i,
    U = (e => (t, ...a) => ({
      _$litType$: e,
      strings: t,
      values: a
    }))(1),
    q = Symbol.for("lit-noChange"),
    Z = Symbol.for("lit-nothing"),
    F = new WeakMap(),
    W = M.createTreeWalker(M, 129, null, !1);
  function G(e, t) {
    if (!Array.isArray(e) || !e.hasOwnProperty("raw")) throw Error("invalid template strings array");
    return void 0 !== E ? E.createHTML(t) : t;
  }
  const K = (e, t) => {
    const a = e.length - 1,
      i = [];
    let n,
      r = 2 === t ? "<svg>" : "",
      o = B;
    for (let t = 0; t < a; t++) {
      const a = e[t];
      let s,
        l,
        d = -1,
        u = 0;
      for (; u < a.length && (o.lastIndex = u, l = o.exec(a), null !== l);) u = o.lastIndex, o === B ? "!--" === l[1] ? o = N : void 0 !== l[1] ? o = I : void 0 !== l[2] ? (V.test(l[2]) && (n = RegExp("</" + l[2], "g")), o = O) : void 0 !== l[3] && (o = O) : o === O ? ">" === l[0] ? (o = null != n ? n : B, d = -1) : void 0 === l[1] ? d = -2 : (d = o.lastIndex - l[2].length, s = l[1], o = void 0 === l[3] ? O : '"' === l[3] ? R : $) : o === R || o === $ ? o = O : o === N || o === I ? o = B : (o = O, n = void 0);
      const c = o === O && e[t + 1].startsWith("/>") ? " " : "";
      r += o === B ? a + P : d >= 0 ? (i.push(s), a.slice(0, d) + x + a.slice(d) + T + c) : a + T + (-2 === d ? (i.push(void 0), t) : c);
    }
    return [G(e, r + (e[a] || "<?>") + (2 === t ? "</svg>" : "")), i];
  };
  class X {
    constructor({
      strings: e,
      _$litType$: t
    }, a) {
      let i;
      this.parts = [];
      let n = 0,
        r = 0;
      const o = e.length - 1,
        s = this.parts,
        [l, d] = K(e, t);
      if (this.el = X.createElement(l, a), W.currentNode = this.el.content, 2 === t) {
        const e = this.el.content,
          t = e.firstChild;
        t.remove(), e.append(...t.childNodes);
      }
      for (; null !== (i = W.nextNode()) && s.length < o;) {
        if (1 === i.nodeType) {
          if (i.hasAttributes()) {
            const e = [];
            for (const t of i.getAttributeNames()) if (t.endsWith(x) || t.startsWith(T)) {
              const a = d[r++];
              if (e.push(t), void 0 !== a) {
                const e = i.getAttribute(a.toLowerCase() + x).split(T),
                  t = /([.?@])?(.*)/.exec(a);
                s.push({
                  type: 1,
                  index: n,
                  name: t[2],
                  strings: e,
                  ctor: "." === t[1] ? te : "?" === t[1] ? ie : "@" === t[1] ? ne : ee
                });
              } else s.push({
                type: 6,
                index: n
              });
            }
            for (const t of e) i.removeAttribute(t);
          }
          if (V.test(i.tagName)) {
            const e = i.textContent.split(T),
              t = e.length - 1;
            if (t > 0) {
              i.textContent = S ? S.emptyScript : "";
              for (let a = 0; a < t; a++) i.append(e[a], D()), W.nextNode(), s.push({
                type: 2,
                index: ++n
              });
              i.append(e[t], D());
            }
          }
        } else if (8 === i.nodeType) if (i.data === j) s.push({
          type: 2,
          index: n
        });else {
          let e = -1;
          for (; -1 !== (e = i.data.indexOf(T, e + 1));) s.push({
            type: 7,
            index: n
          }), e += T.length - 1;
        }
        n++;
      }
    }
    static createElement(e, t) {
      const a = M.createElement("template");
      return a.innerHTML = e, a;
    }
  }
  function Y(e, t, a = e, i) {
    var n, r, o, s;
    if (t === q) return t;
    let l = void 0 !== i ? null === (n = a._$Co) || void 0 === n ? void 0 : n[i] : a._$Cl;
    const d = C(t) ? void 0 : t._$litDirective$;
    return (null == l ? void 0 : l.constructor) !== d && (null === (r = null == l ? void 0 : l._$AO) || void 0 === r || r.call(l, !1), void 0 === d ? l = void 0 : (l = new d(e), l._$AT(e, a, i)), void 0 !== i ? (null !== (o = (s = a)._$Co) && void 0 !== o ? o : s._$Co = [])[i] = l : a._$Cl = l), void 0 !== l && (t = Y(e, l._$AS(e, t.values), l, i)), t;
  }
  class J {
    constructor(e, t) {
      this._$AV = [], this._$AN = void 0, this._$AD = e, this._$AM = t;
    }
    get parentNode() {
      return this._$AM.parentNode;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    u(e) {
      var t;
      const {
          el: {
            content: a
          },
          parts: i
        } = this._$AD,
        n = (null !== (t = null == e ? void 0 : e.creationScope) && void 0 !== t ? t : M).importNode(a, !0);
      W.currentNode = n;
      let r = W.nextNode(),
        o = 0,
        s = 0,
        l = i[0];
      for (; void 0 !== l;) {
        if (o === l.index) {
          let t;
          2 === l.type ? t = new Q(r, r.nextSibling, this, e) : 1 === l.type ? t = new l.ctor(r, l.name, l.strings, this, e) : 6 === l.type && (t = new re(r, this, e)), this._$AV.push(t), l = i[++s];
        }
        o !== (null == l ? void 0 : l.index) && (r = W.nextNode(), o++);
      }
      return W.currentNode = M, n;
    }
    v(e) {
      let t = 0;
      for (const a of this._$AV) void 0 !== a && (void 0 !== a.strings ? (a._$AI(e, a, t), t += a.strings.length - 2) : a._$AI(e[t])), t++;
    }
  }
  class Q {
    constructor(e, t, a, i) {
      var n;
      this.type = 2, this._$AH = Z, this._$AN = void 0, this._$AA = e, this._$AB = t, this._$AM = a, this.options = i, this._$Cp = null === (n = null == i ? void 0 : i.isConnected) || void 0 === n || n;
    }
    get _$AU() {
      var e, t;
      return null !== (t = null === (e = this._$AM) || void 0 === e ? void 0 : e._$AU) && void 0 !== t ? t : this._$Cp;
    }
    get parentNode() {
      let e = this._$AA.parentNode;
      const t = this._$AM;
      return void 0 !== t && 11 === (null == e ? void 0 : e.nodeType) && (e = t.parentNode), e;
    }
    get startNode() {
      return this._$AA;
    }
    get endNode() {
      return this._$AB;
    }
    _$AI(e, t = this) {
      e = Y(this, e, t), C(e) ? e === Z || null == e || "" === e ? (this._$AH !== Z && this._$AR(), this._$AH = Z) : e !== this._$AH && e !== q && this._(e) : void 0 !== e._$litType$ ? this.g(e) : void 0 !== e.nodeType ? this.$(e) : (e => H(e) || "function" == typeof (null == e ? void 0 : e[Symbol.iterator]))(e) ? this.T(e) : this._(e);
    }
    k(e) {
      return this._$AA.parentNode.insertBefore(e, this._$AB);
    }
    $(e) {
      this._$AH !== e && (this._$AR(), this._$AH = this.k(e));
    }
    _(e) {
      this._$AH !== Z && C(this._$AH) ? this._$AA.nextSibling.data = e : this.$(M.createTextNode(e)), this._$AH = e;
    }
    g(e) {
      var t;
      const {
          values: a,
          _$litType$: i
        } = e,
        n = "number" == typeof i ? this._$AC(e) : (void 0 === i.el && (i.el = X.createElement(G(i.h, i.h[0]), this.options)), i);
      if ((null === (t = this._$AH) || void 0 === t ? void 0 : t._$AD) === n) this._$AH.v(a);else {
        const e = new J(n, this),
          t = e.u(this.options);
        e.v(a), this.$(t), this._$AH = e;
      }
    }
    _$AC(e) {
      let t = F.get(e.strings);
      return void 0 === t && F.set(e.strings, t = new X(e)), t;
    }
    T(e) {
      H(this._$AH) || (this._$AH = [], this._$AR());
      const t = this._$AH;
      let a,
        i = 0;
      for (const n of e) i === t.length ? t.push(a = new Q(this.k(D()), this.k(D()), this, this.options)) : a = t[i], a._$AI(n), i++;
      i < t.length && (this._$AR(a && a._$AB.nextSibling, i), t.length = i);
    }
    _$AR(e = this._$AA.nextSibling, t) {
      var a;
      for (null === (a = this._$AP) || void 0 === a || a.call(this, !1, !0, t); e && e !== this._$AB;) {
        const t = e.nextSibling;
        e.remove(), e = t;
      }
    }
    setConnected(e) {
      var t;
      void 0 === this._$AM && (this._$Cp = e, null === (t = this._$AP) || void 0 === t || t.call(this, e));
    }
  }
  class ee {
    constructor(e, t, a, i, n) {
      this.type = 1, this._$AH = Z, this._$AN = void 0, this.element = e, this.name = t, this._$AM = i, this.options = n, a.length > 2 || "" !== a[0] || "" !== a[1] ? (this._$AH = Array(a.length - 1).fill(new String()), this.strings = a) : this._$AH = Z;
    }
    get tagName() {
      return this.element.tagName;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(e, t = this, a, i) {
      const n = this.strings;
      let r = !1;
      if (void 0 === n) e = Y(this, e, t, 0), r = !C(e) || e !== this._$AH && e !== q, r && (this._$AH = e);else {
        const i = e;
        let o, s;
        for (e = n[0], o = 0; o < n.length - 1; o++) s = Y(this, i[a + o], t, o), s === q && (s = this._$AH[o]), r || (r = !C(s) || s !== this._$AH[o]), s === Z ? e = Z : e !== Z && (e += (null != s ? s : "") + n[o + 1]), this._$AH[o] = s;
      }
      r && !i && this.j(e);
    }
    j(e) {
      e === Z ? this.element.removeAttribute(this.name) : this.element.setAttribute(this.name, null != e ? e : "");
    }
  }
  class te extends ee {
    constructor() {
      super(...arguments), this.type = 3;
    }
    j(e) {
      this.element[this.name] = e === Z ? void 0 : e;
    }
  }
  const ae = S ? S.emptyScript : "";
  class ie extends ee {
    constructor() {
      super(...arguments), this.type = 4;
    }
    j(e) {
      e && e !== Z ? this.element.setAttribute(this.name, ae) : this.element.removeAttribute(this.name);
    }
  }
  class ne extends ee {
    constructor(e, t, a, i, n) {
      super(e, t, a, i, n), this.type = 5;
    }
    _$AI(e, t = this) {
      var a;
      if ((e = null !== (a = Y(this, e, t, 0)) && void 0 !== a ? a : Z) === q) return;
      const i = this._$AH,
        n = e === Z && i !== Z || e.capture !== i.capture || e.once !== i.once || e.passive !== i.passive,
        r = e !== Z && (i === Z || n);
      n && this.element.removeEventListener(this.name, this, i), r && this.element.addEventListener(this.name, this, e), this._$AH = e;
    }
    handleEvent(e) {
      var t, a;
      "function" == typeof this._$AH ? this._$AH.call(null !== (a = null === (t = this.options) || void 0 === t ? void 0 : t.host) && void 0 !== a ? a : this.element, e) : this._$AH.handleEvent(e);
    }
  }
  class re {
    constructor(e, t, a) {
      this.element = e, this.type = 6, this._$AN = void 0, this._$AM = t, this.options = a;
    }
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AI(e) {
      Y(this, e);
    }
  }
  const oe = A.litHtmlPolyfillSupport;
  null == oe || oe(X, Q), (null !== (w = A.litHtmlVersions) && void 0 !== w ? w : A.litHtmlVersions = []).push("2.8.0");
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  var se, le;
  class de extends y {
    constructor() {
      super(...arguments), this.renderOptions = {
        host: this
      }, this._$Do = void 0;
    }
    createRenderRoot() {
      var e, t;
      const a = super.createRenderRoot();
      return null !== (e = (t = this.renderOptions).renderBefore) && void 0 !== e || (t.renderBefore = a.firstChild), a;
    }
    update(e) {
      const t = this.render();
      this.hasUpdated || (this.renderOptions.isConnected = this.isConnected), super.update(e), this._$Do = ((e, t, a) => {
        var i, n;
        const r = null !== (i = null == a ? void 0 : a.renderBefore) && void 0 !== i ? i : t;
        let o = r._$litPart$;
        if (void 0 === o) {
          const e = null !== (n = null == a ? void 0 : a.renderBefore) && void 0 !== n ? n : null;
          r._$litPart$ = o = new Q(t.insertBefore(D(), e), e, void 0, null != a ? a : {});
        }
        return o._$AI(e), o;
      })(t, this.renderRoot, this.renderOptions);
    }
    connectedCallback() {
      var e;
      super.connectedCallback(), null === (e = this._$Do) || void 0 === e || e.setConnected(!0);
    }
    disconnectedCallback() {
      var e;
      super.disconnectedCallback(), null === (e = this._$Do) || void 0 === e || e.setConnected(!1);
    }
    render() {
      return q;
    }
  }
  de.finalized = !0, de._$litElement$ = !0, null === (se = globalThis.litElementHydrateSupport) || void 0 === se || se.call(globalThis, {
    LitElement: de
  });
  const ue = globalThis.litElementPolyfillSupport;
  null == ue || ue({
    LitElement: de
  }), (null !== (le = globalThis.litElementVersions) && void 0 !== le ? le : globalThis.litElementVersions = []).push("3.3.3");
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  const ce = (e, t) => "method" === t.kind && t.descriptor && !("value" in t.descriptor) ? {
    ...t,
    finisher(a) {
      a.createProperty(t.key, e);
    }
  } : {
    kind: "field",
    key: Symbol(),
    placement: "own",
    descriptor: {},
    originalKey: t.key,
    initializer() {
      "function" == typeof t.initializer && (this[t.key] = t.initializer.call(this));
    },
    finisher(a) {
      a.createProperty(t.key, e);
    }
  };
  function pe(e) {
    return (t, a) => void 0 !== a ? ((e, t, a) => {
      t.constructor.createProperty(a, e);
    })(e, t, a) : ce(e, t);
    /**
         * @license
         * Copyright 2017 Google LLC
         * SPDX-License-Identifier: BSD-3-Clause
         */
  }
  function me(e) {
    return pe({
      ...e,
      state: !0
    });
  }
  /**
       * @license
       * Copyright 2021 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  var ge;
  null === (ge = window.HTMLSlotElement) || void 0 === ge || ge.prototype.assignedElements;
  let he = !1,
    ve = null;
  const _e = async () => {
    if (he && ve) return ve;
    if (customElements.get("ha-checkbox") && customElements.get("ha-slider") && customElements.get("ha-panel-config") && customElements.get("ha-entity-picker")) return Promise.resolve();
    he = !0, ve = async function () {
      try {
        await new Promise(e => {
          "requestIdleCallback" in window ? requestIdleCallback(() => e()) : setTimeout(() => e(), 0);
        }), await customElements.whenDefined("partial-panel-resolver");
        const e = document.createDocumentFragment(),
          t = document.createElement("partial-panel-resolver");
        e.appendChild(t), t.hass = {
          panels: [{
            url_path: "tmp",
            component_name: "config"
          }]
        }, await new Promise(e => queueMicrotask(() => e())), t._updateRoutes(), await t.routerOptions.routes.tmp.load(), await customElements.whenDefined("ha-panel-config"), await new Promise(e => queueMicrotask(() => e()));
        const a = document.createElement("ha-panel-config");
        e.appendChild(a), await a.routerOptions.routes.automation.load(), customElements.get("ha-entity-picker") || (await Promise.race([customElements.whenDefined("ha-entity-picker"), new Promise(e => setTimeout(e, 3e3))])), e.textContent = "";
      } catch (e) {
        console.error("Failed to load HA form elements:", e);
      }
    }();
    try {
      await ve;
    } finally {
      he = !1, ve = null;
    }
  };
  const be = `v${"2026.06.14"}`,
    fe = "smart_irrigation",
    ke = "metric",
    ze = "bucket",
    ye = e => e.callWS({
      type: fe + "/zones"
    }),
    we = e => e.callWS({
      type: fe + "/irrigation_outlook"
    }),
    Ae = e => {
      class t extends e {
        connectedCallback() {
          super.connectedCallback(), this.__checkSubscribed();
        }
        disconnectedCallback() {
          if (super.disconnectedCallback(), this.__unsubs) {
            for (; this.__unsubs.length;) {
              const e = this.__unsubs.pop();
              e instanceof Promise ? e.then(e => e()) : e();
            }
            this.__unsubs = void 0;
          }
        }
        updated(e) {
          super.updated(e), e.has("hass") && this.__checkSubscribed();
        }
        hassSubscribe() {
          return [];
        }
        __checkSubscribed() {
          void 0 === this.__unsubs && this.isConnected && void 0 !== this.hass && (this.__unsubs = this.hassSubscribe());
        }
      }
      return n([pe({
        attribute: !1
      })], t.prototype, "hass", void 0), t;
    };
  var Se, Ee;
  !function (e) {
    e.Sunrise = "sunrise", e.Sunset = "sunset", e.SolarAzimuth = "solar_azimuth";
  }(Se || (Se = {})), function (e) {
    e.Disabled = "disabled", e.Manual = "manual", e.Automatic = "automatic";
  }(Ee || (Ee = {}));
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  const xe = 2;
  class Te {
    constructor(e) {}
    get _$AU() {
      return this._$AM._$AU;
    }
    _$AT(e, t, a) {
      this._$Ct = e, this._$AM = t, this._$Ci = a;
    }
    _$AS(e, t) {
      return this.update(e, t);
    }
    update(e, t) {
      return this.render(...t);
    }
  }
  /**
       * @license
       * Copyright 2017 Google LLC
       * SPDX-License-Identifier: BSD-3-Clause
       */
  class je extends Te {
    constructor(e) {
      if (super(e), this.et = Z, e.type !== xe) throw Error(this.constructor.directiveName + "() can only be used in child bindings");
    }
    render(e) {
      if (e === Z || null == e) return this.ft = void 0, this.et = e;
      if (e === q) return e;
      if ("string" != typeof e) throw Error(this.constructor.directiveName + "() called with a non-string value");
      if (e === this.et) return this.ft;
      this.et = e;
      const t = [e];
      return t.raw = t, this.ft = {
        _$litType$: this.constructor.resultType,
        strings: t,
        values: []
      };
    }
  }
  je.directiveName = "unsafeHTML", je.resultType = 1;
  const Pe = (e => (...t) => ({
    _$litDirective$: e,
    values: t
  }))(je);
  var Me = {
      actions: {
        delete: "Lösche",
        edit: "Bearbeiten",
        save: "Speichern",
        cancel: "Abbrechen",
        confirm_delete: "Löschen bestätigen",
        confirm_delete_zone: "Möchtest du diese Zone wirklich löschen?"
      },
      labels: {
        module: "Modul",
        no: "Nein",
        select: "Wähle",
        yes: "Ja",
        enabled: "Aktiviert",
        disabled: "Deaktiviert",
        before: "vor",
        after: "nach",
        settings: "Einstellungen",
        bulk_actions: "Sammelaktionen"
      },
      attributes: {
        size: "Größe",
        throughput: "Durchfluss",
        state: "Zustand",
        bucket: "Eimer",
        last_updated: "zuletzt aktualisiert",
        last_calculated: "zuletzt berechnet",
        number_of_data_points: "Anzahl Datenpunkte"
      },
      loading: "Laden",
      saving: "Speichern",
      units: {
        seconds: "Sekunden"
      },
      "loading-messages": {
        configuration: "Konfiguration wird geladen...",
        modules: "Module werden geladen...",
        general: "Laden..."
      },
      "saving-messages": {
        adding: "Hinzufügen...",
        saving: "Speichern..."
      },
      errors: {
        load_failed: "Daten konnten nicht geladen werden",
        save_failed: "Änderungen konnten nicht gespeichert werden",
        delete_failed: "Löschen fehlgeschlagen",
        action_failed: "Aktion fehlgeschlagen"
      }
    },
    De = {
      "default-zone": "Standard Zone",
      "default-mapping": "Standard Sensorgruppe"
    },
    Ce = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Beachte: Diese Beschreibung nutzt '.' als Dezimalzeichen und zeigt gerundete Werte. Das Modul berechnete einen Evapotranspirationsmangel von",
          "bucket-was": "Der alte Vorrat war",
          "new-bucket-values-is": "Der neue Vorrat ist",
          "old-bucket-variable": "alter_Vorrat",
          delta: "Veränderung",
          "bucket-less-than-zero-irrigation-necessary": "Wenn der Vorrat < 0 ist, ist eine Bewässerung nötig.",
          "steps-taken-to-calculate-duration": "Für eine exakte Berechnung der Dauer, wurden folgende Schritte durchgeführt",
          "precipitation-rate-defined-as": "Der Niederschlag ist",
          "duration-is-calculated-as": "Die Dauer ist",
          bucket: "Vorrat",
          "precipitation-rate-variable": "Niederschlag",
          "multiplier-is-applied": "Der Multiplikator wird angewendet. Der Multiplikator ist",
          "duration-after-multiplier-is": "also ist die Dauer",
          "maximum-duration-is-applied": "Die maximale Dauer wird angewendet. Diese ist",
          "duration-after-maximum-duration-is": "also ist die Dauer",
          "lead-time-is-applied": "Zuletzt wird die Vorlaufzeit angewendet. Die Vorlaufzeit ist",
          "duration-after-lead-time-is": "also ist die Dauer",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Wenn der Vorrat >= 0 ist, ist keine Bewässerung nötig und die Dauer ist gleich",
          "maximum-bucket-is": "Der maximale Vorrat ist",
          "max-bucket-variable": "max_bucket",
          drainage: "Drainage",
          "drainage-rate": "Drainagerate",
          hours: "Stunden",
          "drainage-rate-is": "Drainagerate bei Sättigung (Eimer am Maximum) beträgt",
          "current-drainage-is": "Aktuelle Drainage berechnet als",
          "no-drainage": "Aktuelle Drainage ist 0, weil"
        }
      }
    },
    He = {
      pyeto: {
        description: "Die Berechnung der Verunstungsrate basiert auf der FAO56-Formel aus der PyETO-Bibliothek"
      },
      static: {
        description: "Modul mit einer statisch konfigurierbaren Verdunstungsrate."
      },
      passthrough: {
        description: "Pass Through übernimmt den Evapotranspirationssensor und gibt seinen Wert zurück. Auf diese Weise werden alle Berechnungen der Verdunstung umgangen, außer der Anwendung von Aggregaten wie Summe, Durchschnitt etc)."
      }
    },
    Le = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Automatische Berechnung der Bewässerungsdauer",
            description: "Die Berechnung berücksichtigt die bis zu diesem Zeitpunkt gesammelten Wetterdaten und aktualisiert den Vorrat für jede automatische Zone. Anschließend wird die Dauer basierend auf dem neuen Vorrat angepasst und die gesammelten Wetterdaten entfernt.",
            labels: {
              "auto-calc-enabled": "Automatische Berechnung der Dauer pro Zone",
              "auto-calc-time": "Berechne um",
              "calc-time": "Berechnen um"
            }
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Hinweis: Die automatische Aktualisierung der Wetterdaten erfolgt bei oder nach der automatischen Berechnung der Bewässerungsdauer"
            },
            header: "Automatische Aktualisierung der Wetterdaten",
            description: "Die Wetterdaten werden automatisch gesammelt und gespeichert. Zur Berechnung der Zonen und Bewässerungsdauer sind Wetterdaten erforderlich.",
            labels: {
              "auto-update-enabled": "Automatisches Update der Wetterdaten",
              "auto-update-delay": "Update Verzögerung",
              "auto-update-interval": "Update der Sensordaten alle",
              "auto-update-schedule": "Aktualisierungsplan",
              "auto-update-time": "Aktualisieren um"
            },
            options: {
              days: "Tage",
              hours: "Stunden",
              minutes: "Minuten"
            }
          },
          "automatic-clear": {
            header: "Automatisches Löschen der Wetterdaten",
            description: "Gesammelte Wetterdaten zu einem bestimmten Zeitpunkt automatisch entfernen. Damit wird sicher gestellt, dass keine Wetterdaten von vergangenen Tagen übrig bleiben. Entferne die Wetterdaten nicht vor der Berechnung und verwende diese Option nur, wenn du erwartest, dass das automatische Update Wetterdaten erfasst hat, nachdem der Tag berechnet wurde. Idealerweise sollte dieser Schnitt so spät wie möglich Tag durchgeführt werden.",
            labels: {
              "automatic-clear-enabled": "Automatisches Löschen der Wetterdaten",
              "automatic-clear-time": "Löschen der Wetterdaten um"
            }
          },
          continuousupdates: {
            header: "Kontinuierliche Sensoraktualisierungen (experimentell)",
            description: "Experimentelle Funktion für granularere Wetterdaten.",
            labels: {
              continuousupdates: "Kontinuierliche Aktualisierungen aktivieren",
              sensor_debounce: "Sensor-Entprellung",
              "sensor-debounce": "Sensor-Entprellzeit (ms)"
            }
          }
        },
        description: "Diese Seite ist für allgemeine Einstellungen.",
        title: "Allgemein",
        sections: {
          weather: "Wetter",
          automation: "Automatisierung",
          location: "Standort",
          watering: "Bewässerungsverhalten"
        }
      },
      help: {
        title: "Hilfe",
        cards: {
          "how-to-get-help": {
            title: "Hilfe bekommen",
            "first-read-the": "Lies zuerst im",
            wiki: "Dokumentation",
            "if-you-still-need-help": "Benötigst du weiterhin Hilfe, wende dich an das",
            "community-forum": "Community Forum",
            "or-open-a": "oder eröffne einen",
            "github-issue": "GitHub-Issue",
            "english-only": "nur Englisch"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Hinzufügen"
            },
            header: "Sensorgruppe hinzufügen"
          },
          mapping: {
            aggregates: {
              average: "Durchschnitt",
              first: "Erster",
              last: "Letzter",
              maximum: "Maximum",
              median: "Median",
              minimum: "Minimum",
              sum: "Summe",
              riemannsum: "Riemann-Summe",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Diese Sensorgruppe kann nicht entfernt werden, da sie von mindestens einer Zone verwendet wird.",
              invalid_source: "Ungültige Quelle",
              source_does_not_exist: "Quelle existiert nicht. Bitte gib eine gültige Quelle ein, z. B. 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Taupunkt",
              evapotranspiration: "Verdunstung",
              humidity: "Feuchtigkeit",
              "maximum temperature": "Maximum-Temperatur",
              "minimum temperature": "Minimum-Temperatur",
              precipitation: "Gesamtniederschlag",
              pressure: "Luftdruck",
              "solar radiation": "Sonnenstrahlung",
              temperature: "Temperatur",
              windspeed: "Windgeschwindigkeit",
              "current precipitation": "Aktueller Niederschlag"
            },
            pressure_types: {
              absolute: "absolut",
              relative: "relativ"
            },
            "pressure-type": "Der Luftdruck ist",
            "sensor-aggregate-of-sensor-values-to-calculate": "des Sensors für die Berechnung.",
            "sensor-aggregate-use-the": "Nutze den/die/das",
            "sensor-entity": "Sensor Entität",
            static_value: "Wert",
            "input-units": "Sensor Werte in",
            source: "Quelle",
            sources: {
              none: "Keine",
              weather_service: "Wetterdienst",
              sensor: "Sensor",
              static: "Fester Wert"
            }
          }
        },
        description: "Füge eine oder mehrere Sensorgruppen hinzu, die Wetterdaten von Weather service, Sensoren oder einer Kombination daraus abrufen. Jede Sensorgruppe kann für eine oder mehrere Zonen verwendet werden",
        labels: {
          "mapping-name": "Name"
        },
        no_items: "Es ist noch keine Sensorgruppe angelegt.",
        title: "Sensorgruppen",
        "weather-records": {
          title: "Wetterdaten",
          timestamp: "Zeit",
          temperature: "Temp.",
          humidity: "Feuchte",
          dewpoint: "Taupunkt",
          wind: "Wind",
          pressure: "Druck",
          precipitation: "Niederschlag",
          "retrieval-time": "Abgerufen",
          "no-data": "Keine Wetterdaten für diese Sensorgruppe verfügbar"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Hinzufügen"
            },
            header: "Modul hinzufügen"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Dieses Modul kann nicht entfernt werden, da es von mindestens einer Zone verwendet wird."
            },
            labels: {
              configuration: "Konfiguration",
              required: "Feld ist erforderlich"
            },
            "translated-options": {
              DontEstimate: "Nicht berechnen",
              EstimateFromSunHours: "Basierend auf den Sonnenstunden",
              EstimateFromTemp: "Basierend auf der Temperatur",
              EstimateFromSunHoursAndTemperature: "Basierend auf dem Durchschnitt von Sonnenstunden und Temperatur"
            }
          }
        },
        description: "Füge ein oder mehrere Module hinzu. Module berechnen die Bewässerungsdauer. Jedes Modul hat seine eigene Konfiguration und kann zur Berechnung der Bewässerungsdauer für eine oder mehrere Zonen verwendet werden.",
        no_items: "Es ist noch kein Module angelegt.",
        title: "Module"
      },
      zones: {
        actions: {
          add: "Hinzufügen",
          calculate: "Bewässerungsdauer berechnen.",
          information: "Informationen",
          update: "Wetterdaten aktualisieren.",
          "reset-bucket": "Vorrat zurücksetzen",
          "view-weather-info": "Wetterdaten anzeigen",
          "view-weather-info-message": "Wetterdaten verfügbar für",
          "view-watering-calendar": "Bewässerungskalender",
          irrigate_all: "Alle Zonen jetzt bewässern",
          open_settings: "Einstellungen bearbeiten"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Hinzufügen"
            },
            header: "Zone hinzufügen"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Dauern neu berechnen",
              "update-all": "Wetterdaten aktualisieren",
              "reset-all-buckets": "Alle Vorräte zurücksetzen",
              "clear-all-weatherdata": "Alle Wetterdaten löschen"
            },
            header: "Aktionen für alle Zonen"
          }
        },
        description: "Füge eine oder mehrere Zonen hinzu. Die Bewässerungsdauer wird pro Zone, abhängig von Größe, Durchsatz, Status, Modul und Sensorgruppe berechnet.",
        labels: {
          bucket: "Vorrat",
          duration: "Dauer",
          "lead-time": "Vorlaufzeit",
          mapping: "Sensorgruppe",
          "maximum-duration": "Maximale Dauer",
          multiplier: "Multiplikator",
          name: "Name",
          size: "Größe",
          state: "Berechnung",
          states: {
            automatic: "Automatisch",
            disabled: "Aus",
            manual: "Manuell"
          },
          throughput: "Durchfluss",
          "maximum-bucket": "Maximaler Vorrat",
          last_calculated: "Zuletzt berechnet",
          "data-last-updated": "Daten zuletzt aktualisiert",
          "data-number-of-data-points": "Anzahl der Messungen",
          drainage_rate: "Drainagerate",
          linked_entity: "Verknüpfte Schalter/Ventil-Entität",
          linked_entity_placeholder: "z.B. switch.garten_ventil",
          irrigate_now: "Jetzt bewässern",
          bucket_threshold: "Mindestdefizit für Bewässerung",
          flow_sensor: "Durchflussmesser-Sensor (optional)",
          flow_sensor_placeholder: "z. B. sensor.zone_flow_rate"
        },
        no_items: "Es ist noch keine Zone vorhanden.",
        title: "Zonen",
        confirm_irrigate: {
          title: "Bewässerung starten?",
          body: "Dies öffnet jetzt die verknüpften Ventile und umgeht alle Ausschlussbedingungen (Regen, Temperatur, Mindestabstand zwischen Bewässerungen).",
          all_linked_zones: "Alle verknüpften Zonen",
          toast_started: "Bewässerung gestartet",
          toast_failed: "Bewässerung fehlgeschlagen"
        },
        status: {
          decision_disabled: "Ausgeschaltet — diese Zone wird nicht automatisch bewässert.",
          decision_water: "Bewässerung nötig: etwa {duration} beim nächsten geplanten Lauf.",
          decision_water_at: "Bewässert etwa {duration} um {time}.",
          decision_water_skip: "Defizit ~{duration}, aber der nächste Lauf wird wahrscheinlich übersprungen ({reason}).",
          decision_water_no_schedule: "Defizit ~{duration} — kein Zeitplan bewässert diese Zone; manuell starten.",
          decision_no_water: "Derzeit keine Bewässerung nötig — der Boden hat genug Feuchtigkeit.",
          decision_unknown: "Noch nicht berechnet — auf Aktualisieren und dann Berechnen drücken.",
          last_checked: "Zuletzt geprüft",
          never: "nie",
          saved: "Gespeichert",
          estimate_now: "Jetzt",
          estimate_tag: "gesch.",
          estimate_method: {
            hourly: "Live-Schätzung aus stündlichem Wetter seit der letzten Berechnung",
            proxy: "Schätzung aus der heutigen Vorhersage seit der letzten Berechnung"
          }
        },
        help: {
          bucket: "Bodenfeuchte-Bilanz (Vorrat). Ein negativer Wert bedeutet, dass der Boden trocken ist und die Zone Wasser braucht.",
          calculate: "Berechnet aus den neuesten Daten, wie lange bewässert wird. Nach dem Aktualisieren ausführen.",
          update: "Ruft die neuesten Wetter-/Sensordaten für diese Zone ab.",
          irrigate_link_entity: "Verknüpfe in den Zoneneinstellungen einen Schalter/ein Ventil, um manuelle Bewässerung zu ermöglichen.",
          irrigate_all: "Öffnet jetzt die verknüpften Ventile für jede Zone mit Defizit. Überspring-Bedingungen (Regen, Wind, Temperatur) werden ignoriert.",
          update_all: "Sammelt die neuesten Wetter-/Sensordaten für alle Zonen. Ändert die Dauern nicht von selbst.",
          calculate_all: "Berechnet die Bewässerungsdauer jeder automatischen Zone aus den bisher gesammelten Daten neu."
        },
        outlook: {
          next_run: "Nächster Lauf",
          no_schedule: "Kein automatischer Zeitplan — Zonen bewässern nur, wenn du sie auslöst.",
          setup_schedule: "Zeitplan einrichten",
          targets_all: "alle Zonen",
          targets_zones: "{count} Zonen",
          will_skip: "Nächster Lauf wird wahrscheinlich übersprungen",
          will_run: "Bedingungen für den nächsten Lauf sehen gut aus.",
          why_skipped: "Warum?",
          provisional: "Vorhersage — kann sich ändern",
          active_guards: "Aktive Bedingungen",
          last_run: "Letzter Lauf",
          last_run_skipped: "übersprungen",
          last_run_ran: "ausgeführt",
          today: "heute",
          tomorrow: "morgen",
          actions: {
            irrigate: "Bewässern",
            calculate: "Neu berechnen",
            update: "Daten aktualisieren"
          },
          checks: {
            precipitation: "Regenvorhersage",
            days_between: "Tage zwischen Bewässerungen",
            temperature: "Niedrige Temperatur",
            wind: "Starker Wind",
            rain_sensor: "Regensensor"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} Tage",
            temperature: "{observed}° (unter {threshold}°)",
            wind: "{observed} (über {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Keine Bewässerungskalender-Daten für diese Zone verfügbar.",
          error_prefix: "Fehler beim Erstellen des Kalenders:",
          month: "Monat",
          et: "ET (mm)",
          precipitation: "Niederschlag (mm)",
          watering: "Bewässerung (L)",
          avg_temp: "Ø Temp (°C)",
          method_prefix: "Methode:"
        },
        confirm_action: {
          reset_bucket_title: "Vorrat dieser Zone zurücksetzen?",
          reset_bucket_body: "Dies setzt den Vorrat auf 0 zurück und verwirft die angesammelte Feuchtigkeitsbilanz dieser Zone.",
          reset_all_buckets_title: "Alle Vorräte zurücksetzen?",
          reset_all_buckets_body: "Dies setzt den Vorrat jeder Zone auf 0 zurück und verwirft die angesammelte Feuchtigkeitsbilanz. Die Bewässerungsberechnung beginnt beim nächsten Update neu.",
          clear_weather_title: "Alle Wetterdaten löschen?",
          clear_weather_body: "Dies löscht alle gesammelten Wetter- und Sensordaten aller Zonen. Die Zonen benötigen neue Daten, bevor sie wieder berechnen können."
        }
      },
      schedules: {
        title: "Zeitpläne",
        description: "Erstellen Sie wiederkehrende Zeitpläne für automatische Berechnung, Aktualisierung oder Bewässerung – ohne Automationen.",
        add: "Zeitplan hinzufügen",
        no_items: "Noch keine Zeitpläne konfiguriert. Klicken Sie auf 'Zeitplan hinzufügen'.",
        zones_all: "Alle Zonen",
        zones_specific: "Bestimmte Zonen",
        hours: "Stunden",
        minutes: "Min",
        types: {
          daily: "Täglich",
          weekly: "Wöchentlich",
          monthly: "Monatlich",
          interval: "Alle N Stunden",
          sunrise: "Sonnenaufgang",
          sunset: "Sonnenuntergang",
          solar_azimuth: "Sonnenazimut"
        },
        actions: {
          calculate: "Berechnen (Bewässerungsdauer aktualisieren)",
          update: "Aktualisieren (Wetterdaten sammeln)",
          irrigate: "Bewässern (Ventile direkt steuern)"
        },
        days: {
          monday: "Mo",
          tuesday: "Di",
          wednesday: "Mi",
          thursday: "Do",
          friday: "Fr",
          saturday: "Sa",
          sunday: "So"
        },
        fields: {
          name: "Name",
          type: "Zeitplantyp",
          enabled: "Aktiviert",
          time: "Uhrzeit (HH:MM)",
          days_of_week: "Wochentage",
          day_of_month: "Tag des Monats",
          interval_hours: "Intervall",
          action: "Aktion",
          zones: "Zonen",
          start_date: "Startdatum (optional)",
          end_date: "Enddatum (optional)",
          offset_minutes: "Versatz von Sonnenaufgang/-untergang",
          account_for_duration: "Früh starten, damit Bewässerung zur Zielzeit endet",
          azimuth_angle: "Sonnenazimutwinkel",
          time_anchor: "Zeitpunkt markiert"
        },
        dialog: {
          add_title: "Zeitplan hinzufügen",
          edit_title: "Zeitplan bearbeiten"
        },
        time_anchor: {
          start: "Beginn der Bewässerung",
          finish: "Ende der Bewässerung"
        }
      },
      info: {
        title: "Info",
        description: "Nächste Bewässerung und Systemstatus anzeigen.",
        "configuration-not-available": "Konfiguration nicht verfügbar.",
        cards: {
          "zone-bucket-values": {
            title: "Zoneneimerstand & Dauer",
            labels: {
              bucket: "Eimer",
              duration: "Dauer"
            },
            "no-zones": "Keine Zonen konfiguriert"
          },
          "next-irrigation": {
            title: "Nächste Bewässerung",
            labels: {
              "next-start": "Nächster Start",
              duration: "Dauer",
              zones: "Zonen"
            },
            "no-data": "Keine Daten verfügbar"
          },
          "irrigation-reason": {
            title: "Bewässerungsgrund",
            labels: {
              reason: "Grund",
              sunrise: "Sonnenaufgang",
              "total-duration": "Gesamtdauer",
              explanation: "Erklärung"
            },
            "no-data": "Keine Daten verfügbar"
          },
          irrigate_now: {
            title: "Jetzt bewässern",
            description: "Bewässerung sofort für alle Zonen mit verknüpfter Entität starten. Übersprungbedingungen werden ignoriert.",
            button_all: "Alle Zonen jetzt starten",
            no_linked_zones: "Keine Zonen haben eine verknüpfte Schalter/Ventil-Entität mit berechneter Dauer."
          }
        }
      },
      setup: {
        title: "Einrichtung"
      }
    },
    Be = "Smart Irrigation",
    Ne = {
      title: "Standortkoordinaten",
      description: "Konfigurieren Sie Standortkoordinaten für den Abruf von Wetterdaten. Sie können manuelle Koordinaten verwenden, die sich von Ihrem Home Assistant Standort unterscheiden.",
      manual_enabled: "Manuelle Koordinaten verwenden",
      use_ha_location: "Home Assistant Standort verwenden",
      latitude: "Breitengrad (Dezimalgrad)",
      longitude: "Längengrad (Dezimalgrad)",
      elevation: "Höhe (Meter über dem Meeresspiegel)",
      current_ha_coords: "Aktuelle Home Assistant Koordinaten"
    },
    Ie = {
      title: "Tage zwischen Bewässerungen",
      description: "Konfigurieren Sie die Mindestanzahl an Tagen zwischen Bewässerungsereignissen.",
      label: "Minimale Tage zwischen Bewässerungen",
      help_text: "Auf 0 setzen zum Deaktivieren. Werte von 1–365 Tagen werden unterstützt."
    },
    Oe = {
      title: "Bewässerungsstart-Auslöser",
      description: "Konfiguriere, wann die Bewässerung auf Basis von Sonnenereignissen starten soll. Du kannst mehrere Auslöser für verschiedene Zeitpläne hinzufügen. Bei Sonnenaufgang-Auslösern wird mit einem Versatz von 0 automatisch die Gesamtdauer aller aktivierten Zonen verwendet.",
      add_trigger: "Auslöser hinzufügen",
      edit_trigger: "Auslöser bearbeiten",
      delete_trigger: "Auslöser löschen",
      trigger_types: {
        sunrise: "Sonnenaufgang",
        sunset: "Sonnenuntergang",
        solar_azimuth: "Sonnenazimut"
      },
      fields: {
        name: {
          name: "Auslösername",
          description: "Ein aussagekräftiger Name zur Identifizierung dieses Auslösers"
        },
        type: {
          name: "Auslösertyp",
          description: "Die Art des Sonnenereignisses, das den Auslöser auslöst"
        },
        enabled: {
          name: "Aktiviert",
          description: "Ob dieser Auslöser derzeit aktiv ist"
        },
        offset_minutes: {
          name: "Versatz (Minuten)",
          description: "Minuten vor (-) oder nach (+) dem Sonnenereignis. Verwende bei Sonnenaufgang-Auslösern 0 für eine automatische Zeitsteuerung auf Basis der gesamten Zonendauer."
        },
        azimuth_angle: {
          name: "Azimutwinkel (Grad)",
          description: "Sonnenazimutwinkel in Grad, wobei 0=Nord, 90=Ost, 180=Süd, 270=West"
        },
        account_for_duration: {
          name: "Dauer berücksichtigen",
          description: "Wenn aktiviert, startet die Bewässerung früh genug, um zum angegebenen Zeitpunkt fertig zu sein. Wenn deaktiviert, startet die Bewässerung genau zum angegebenen Zeitpunkt."
        }
      },
      dialog: {
        add_title: "Bewässerungsstart-Auslöser hinzufügen",
        edit_title: "Bewässerungsstart-Auslöser bearbeiten",
        cancel: "Abbrechen",
        save: "Speichern",
        delete: "Löschen"
      },
      no_triggers: "Keine Bewässerungsstart-Auslöser konfiguriert. Das System verwendet das Standardverhalten (Sonnenaufgang mit der Gesamtdauer aller Zonen). Füge Auslöser hinzu, um den Bewässerungsstart anzupassen.",
      offset_auto: "Automatisch (aus der Gesamtdauer aller Zonen berechnet)",
      confirm_delete: "Möchtest du den Auslöser '{name}' wirklich löschen?",
      validation: {
        name_required: "Auslösername ist erforderlich",
        azimuth_invalid: "Der Azimutwinkel muss eine gültige Zahl sein"
      },
      help: {
        sunrise_offset: "Für Sonnenaufgang-Auslöser: Verwende negative Werte, um vor Sonnenaufgang zu starten, positive, um danach zu starten. Setze auf 0, um automatisch früh genug zu starten, damit alle Zonen vor Sonnenaufgang fertig sind.",
        sunset_offset: "Für Sonnenuntergang-Auslöser: Verwende negative Werte, um vor Sonnenuntergang zu starten, positive, um nach Sonnenuntergang zu starten.",
        azimuth_explanation: "Der Sonnenazimut ist die Himmelsrichtung der Sonne. 0°=Nord, 90°=Ost, 180°=Süd, 270°=West. Du kannst einen beliebigen Winkelwert eingeben (z. B. 450° = 90°, -30° = 330°). Nutze dies, um die Bewässerung auszulösen, wenn die Sonne eine bestimmte Position erreicht.",
        multiple_triggers: "Du kannst mehrere Auslöser konfigurieren. Jeder aktivierte Auslöser plant den Bewässerungsstart unabhängig."
      }
    },
    $e = {
      title: "Übersprungbedingungen",
      description: "Bewässerung automatisch überspringen, wenn die Bedingungen ungünstig sind. Niederschlagsprüfung, Temperatur und Wind erfordern einen Wetterdienst.",
      threshold_label: "Niederschlagsschwelle",
      threshold_description: "Mindestmenge an prognostiziertem Gesamtniederschlag (in mm) über das Vorhersagefenster, um die Bewässerung zu überspringen.",
      lookahead_label: "Vorhersage-Fenster (Tage)",
      lookahead_help: "Wie viele kommende Vorhersagetage beim Regen-Check zusammengezählt werden. Die Vorhersage beginnt morgen (heute ausgeschlossen), also 1 = nur der nächste Tag, 2 = die nächsten zwei Tage usw.",
      temp_section_title: "Bei niedriger Temperatur überspringen",
      temp_threshold_label: "Überspringen wenn Temperatur unter",
      wind_section_title: "Bei hoher Windgeschwindigkeit überspringen",
      wind_threshold_label: "Überspringen wenn Windgeschwindigkeit über",
      rain_sensor_section_title: "Regenmelder-Bedingung",
      rain_sensor_label: "Regenmelder-Entität (optional)",
      rain_sensor_placeholder: "z.B. binary_sensor.regen"
    },
    Re = {
      title: "Zonenreihenfolge",
      description: "Wenn mehrere Zonen bewässert werden müssen, legen Sie fest, ob alle gleichzeitig oder nacheinander laufen. Im sequenziellen Modus wartet das System, bis jede Zone fertig ist, bevor die nächste beginnt.",
      parallel: "Parallel (alle Zonen gleichzeitig)",
      sequential: "Sequenziell (eine Zone nach der anderen)",
      rotating: "Rotierend (Zonen wechseln sich ab)",
      max_consecutive_duration_label: "Max. ununterbrochene Laufzeit pro Zone",
      max_consecutive_duration_unit: "Minuten",
      min_absorption_time_label: "Min. Aufnahmezeit zwischen den Durchgängen",
      min_absorption_time_unit: "Minuten (0 = deaktiviert)"
    },
    Ve = {
      title: "Wetterdienst",
      description: "Konfiguriere, welcher Wetterdienst für ET-Berechnungen und Überspringbedingungen verwendet wird.",
      enabled_label: "Wetterdienst aktivieren",
      service_label: "Wetterdienst",
      api_key_label: "API-Schlüssel",
      api_key_placeholder: "Leer lassen, um den vorhandenen Schlüssel zu behalten",
      api_key_configured: "API-Schlüssel ist konfiguriert",
      api_key_not_configured: "Kein API-Schlüssel konfiguriert",
      api_key_help: "Ein API-Schlüssel von deinem gewählten Wetterdienstanbieter. Open-Meteo benötigt keinen Schlüssel. OpenWeatherMap und Pirate Weather bieten beide kostenlose Kontingente.",
      no_api_key_needed: "Open-Meteo ist ein kostenloser Dienst und benötigt keinen API-Schlüssel.",
      save_button: "Wettereinstellungen speichern",
      saved: "Wettereinstellungen gespeichert",
      openmeteo: "Open-Meteo (kostenlos, kein Schlüssel nötig)",
      test_button: "Verbindung testen",
      test_button_testing: "Wird getestet…",
      test_success: "✓ Verbindung erfolgreich",
      test_error_invalid_auth: "✗ Ungültiger API-Schlüssel — prüfe, ob er korrekt und aktiv ist",
      test_error_cannot_connect: "✗ Verbindung nicht möglich — prüfe deine Internetverbindung",
      test_error_no_service: "✗ Wähle zuerst einen Wetterdienst",
      test_error_unknown: "✗ Test fehlgeschlagen — unbekannter Fehler",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    Ue = {
      zone_size: "Die gesamte bewässerte Fläche dieser Zone. Wird zusammen mit dem Durchsatz verwendet, um zu berechnen, wie viel Wasser pro Durchgang ausgebracht wird.",
      zone_throughput: "Gesamtwasserdurchfluss deines Bewässerungssystems für diese Zone (Liter/Min im metrischen System, Gal/Min im imperialen System). Prüfe das Datenblatt deiner Sprinkler oder miss, wie lange das Füllen eines bekannten Behälters dauert.",
      zone_drainage_rate: "Wie schnell überschüssiges Wasser aus dem Boden abfließt, wenn der Eimer voll ist. Typisch: Rasen 50 mm/h, sandiger Boden 100+ mm/h, Lehm 10 mm/h.",
      zone_bucket: "Aktuelles Wasserdefizit (negativ) oder -überschuss (positiv) für diese Zone. Die Bewässerung wird ausgelöst, wenn der Eimer unter den Schwellenwert fällt.",
      zone_maximum_bucket: "Maximaler Feuchtigkeitsüberschuss, den die Zone aufnehmen kann. Wasser über diesem Wert wird als Abfluss behandelt. Typischer Wert: 50 mm.",
      zone_bucket_threshold: "Die Bewässerung wird ausgelöst, wenn der Eimer unter diesen Wert fällt. Muss 0 oder negativ sein. 0 bedeutet, immer dann zu bewässern, wenn ein Defizit besteht.",
      zone_multiplier: "Skalierungsfaktor, der auf die berechnete Dauer angewendet wird. Über 1,0 erhöht, unter 1,0 verringert. Nützlich zur Feinabstimmung, ohne physische Messwerte zu ändern.",
      zone_lead_time: "Zusätzliche Sekunden vor dem Start der Bewässerung. Nutze dies für das Aufwärmen der Pumpe oder den Druckaufbau im System.",
      zone_maximum_duration: "Harte Obergrenze für einen einzelnen Bewässerungsdurchgang in Sekunden. Verhindert unkontrolliertes Bewässern. Standard: 3600 s (1 Stunde).",
      zone_linked_entity: "Die HA-Schalter- oder Ventil-Entität, die den Wasserfluss für diese Zone steuert. Diese Entität wird eingeschaltet, wenn die Bewässerung läuft.",
      zone_flow_sensor: "Optionaler Sensor zur Messung der tatsächlichen Durchflussrate. Wird nur zur Anzeige verwendet — beeinflusst die Dauerberechnung nicht.",
      general_autoupdatedelay: "Sekunden, die nach dem HA-Start bis zum ersten Abruf der Wetterdaten gewartet wird. Ermöglicht es anderen Integrationen, sich zuerst zu initialisieren.",
      general_sensor_debounce: "Mindestabstand in Millisekunden zwischen Sensormesswerten, um Rauschen von sich schnell ändernden Sensoren herauszufiltern.",
      general_calctime: "Tageszeit, zu der die Bewässerungsdauern aus den gesammelten Wetterdaten neu berechnet werden. Format: HH:MM (24-Stunden).",
      general_cleardatatime: "Tageszeit, zu der alte Wetterdaten gelöscht werden. Muss später als die Berechnungszeit eingestellt sein.",
      general_days_between: "Mindestanzahl an Tagen zwischen Bewässerungsereignissen für dieselbe Zone. Auf 0 setzen, um zu deaktivieren (bewässern, sobald ein Defizit besteht).",
      general_autoupdateinterval: "Wie oft Wetterdaten gesammelt werden. Wähle einen Wert, der frische Daten gegen API-Ratenbegrenzungen abwägt.",
      general_precipitation_threshold: "Die Bewässerung wird übersprungen, wenn der vorhergesagte Gesamtniederschlag über das Vorhersagefenster diesen Wert überschreitet.",
      general_temp_threshold: "Die Bewässerung wird übersprungen, wenn die aktuelle Temperatur unter diesem Wert liegt (z. B. zur Vermeidung von Frostschäden).",
      general_wind_threshold: "Die Bewässerung wird übersprungen, wenn die Windgeschwindigkeit diesen Wert überschreitet (starker Wind verringert die Effizienz und verursacht Abdrift)."
    },
    qe = {
      title: "Einrichtungsassistent",
      open_button: "Einrichtungsassistent",
      close: "Schließen",
      next: "Weiter",
      back: "Zurück",
      finish: "Fertigstellen",
      skip_step: "Diesen Schritt überspringen",
      step_indicator: "Schritt {current} von {total}",
      setup_complete_banner: "Einrichtung nicht abgeschlossen. Starte den Assistenten, um zu beginnen.",
      open_wizard: "Assistent öffnen",
      steps: {
        welcome: {
          title: "Willkommen bei Smart Irrigation",
          intro: "Dieser Assistent führt dich durch die vier Schritte, die nötig sind, damit deine erste Zone automatisch bewässert.",
          step1_label: "Wetterdienst — woher die Wetterdaten kommen",
          step2_label: "Berechnungsmodul — wie die Bewässerungsdauer berechnet wird",
          step3_label: "Sensorgruppe — welche Datenquellen verwendet werden",
          step4_label: "Zone — deine erste Bewässerungszone",
          tip: "Du kannst jeden Schritt überspringen und ihn später über den Tab „Einrichtung“ konfigurieren."
        },
        weather: {
          title: "Wetterdienst",
          description: "Wähle, wie Wetterdaten bezogen werden. Open-Meteo ist kostenlos und benötigt keinen API-Schlüssel — für die meisten Nutzer die einfachste Wahl."
        },
        module: {
          title: "Berechnungsmodul",
          description: "Ein Modul berechnet anhand der Evapotranspiration (ET), wie lange bewässert wird. Das PyETO-Modul (FAO-56-Methode) wird für die meisten Nutzer empfohlen.",
          pick_label: "Modultyp auswählen",
          no_modules: "Keine Modultypen verfügbar."
        },
        mapping: {
          title: "Sensorgruppe",
          description: "Eine Sensorgruppe verknüpft jede Wettervariable mit einer Datenquelle. Lege die wichtigsten Variablen unten fest — einzelne Sensorzuordnungen kannst du später über den Tab „Einrichtung → Sensorgruppen“ verfeinern.",
          name_label: "Name der Sensorgruppe",
          source_label: "Datenquelle für",
          use_weather_service: "Wetterdienst",
          use_sensor: "Sensor",
          use_static: "Statischer Wert",
          use_none: "Keine / nicht verwendet"
        },
        zone: {
          title: "Erste Zone",
          description: "Eine Zone ist ein Bewässerungsbereich (z. B. Rasen, Beet). Lege die physischen Eigenschaften fest, damit das System die korrekte Bewässerungsdauer berechnen kann.",
          name_label: "Zonenname",
          size_label: "Fläche",
          throughput_label: "Sprinkler-Durchsatz",
          entity_label: "Verknüpfter Schalter oder Ventil",
          entity_placeholder: "z. B. switch.garden_valve",
          module_label: "Berechnungsmodul",
          mapping_label: "Sensorgruppe"
        },
        done: {
          title: "Einrichtung abgeschlossen!",
          description: "Deine erste Zone ist bereit. Smart Irrigation berechnet die Bewässerungsdauern nun automatisch auf Basis der Wetterdaten.",
          next_steps: "Was du als Nächstes tun kannst:",
          tip1: "Gehe zu „Zonen“, um die berechneten Dauern und Eimerwerte anzuzeigen.",
          tip2: "Füge über den Tab „Zonen“ weitere Zonen hinzu.",
          tip3: "Verfeinere alle Einstellungen über den Tab „Einrichtung“.",
          go_zones: "Zu „Zonen“",
          go_setup: "Zur Einrichtung"
        }
      },
      stepper: {
        weather: "Wetter",
        module: "Modul",
        mapping: "Sensorgruppe",
        zone: "Zone"
      },
      confirm_close: {
        body: "Setup-Assistenten schließen? Dein bisheriger Fortschritt ist gespeichert.",
        keep: "Weiter bearbeiten",
        close: "Schließen"
      }
    },
    Ze = {
      common: Me,
      defaults: De,
      module: Ce,
      calcmodules: He,
      panels: Le,
      title: Be,
      coordinate_config: Ne,
      days_between_irrigation: Ie,
      irrigation_start_triggers: Oe,
      weather_skip: $e,
      zone_sequencing: Re,
      weather_service_config: Ve,
      field_help: Ue,
      wizard: qe
    },
    Fe = Object.freeze({
      __proto__: null,
      common: Me,
      defaults: De,
      module: Ce,
      calcmodules: He,
      panels: Le,
      title: Be,
      coordinate_config: Ne,
      days_between_irrigation: Ie,
      irrigation_start_triggers: Oe,
      weather_skip: $e,
      zone_sequencing: Re,
      weather_service_config: Ve,
      field_help: Ue,
      wizard: qe,
      default: Ze
    }),
    We = {
      loading: "Loading",
      saving: "Saving",
      actions: {
        delete: "Delete",
        edit: "Edit",
        save: "Save",
        cancel: "Cancel",
        confirm_delete: "Confirm Delete",
        confirm_delete_zone: "Are you sure you want to delete this zone?"
      },
      labels: {
        module: "Module",
        no: "No",
        select: "Select",
        yes: "Yes",
        enabled: "Enabled",
        disabled: "Disabled",
        before: "before",
        after: "after",
        settings: "Settings",
        bulk_actions: "Bulk Actions"
      },
      units: {
        seconds: "seconds"
      },
      attributes: {
        size: "size",
        throughput: "throughput",
        state: "state",
        bucket: "bucket",
        last_updated: "last updated",
        last_calculated: "last calculated",
        number_of_data_points: "number of data points"
      },
      "loading-messages": {
        configuration: "Loading configuration...",
        modules: "Loading modules...",
        general: "Loading..."
      },
      "saving-messages": {
        adding: "Adding...",
        saving: "Saving..."
      },
      errors: {
        load_failed: "Couldn't load data",
        save_failed: "Couldn't save changes",
        delete_failed: "Couldn't delete",
        action_failed: "Action failed"
      }
    },
    Ge = {
      "default-zone": "Default zone",
      "default-mapping": "Default sensor group"
    },
    Ke = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Note: this explanation uses '.' as decimal separator, shows rounded and metric values. Module returned Evapotranspiration deficiency ( = et0 * hour_multiplier + precipitation) of",
          "bucket-was": "Bucket was",
          "new-bucket-values-is": "New bucket value is",
          bucket: "bucket",
          "old-bucket-variable": "old_bucket",
          "max-bucket-variable": "max_bucket",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Since bucket < 0, irrigation is necessary",
          "steps-taken-to-calculate-duration": "To calculate the exact duration, the following steps were taken",
          "precipitation-rate-defined-as": "The precipitation rate is defined as",
          "duration-is-calculated-as": "The duration is calculated as",
          drainage: "drainage",
          "drainage-rate": "drainage_rate",
          hours: "hours",
          "precipitation-rate-variable": "precipitation_rate",
          "multiplier-is-applied": "Now, the multiplier is applied. The multiplier is",
          "duration-after-multiplier-is": "hence the duration is",
          "maximum-duration-is-applied": "Then, the maximum duration is applied. The maximum duration is",
          "duration-after-maximum-duration-is": "hence the duration is",
          "lead-time-is-applied": "Finally, the lead time is applied. The lead time is",
          "duration-after-lead-time-is": "hence the final duration is",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Since bucket >= 0, no irrigation is necessary and duration is set to",
          "maximum-bucket-is": "Maximum bucket size is",
          "drainage-rate-is": "Drainage rate when saturated (bucket at max) is",
          "current-drainage-is": "Current drainage is calculated as",
          "no-drainage": "Current drainage is 0 because"
        }
      }
    },
    Xe = {
      pyeto: {
        description: "Calculate duration based on the FAO56 calculation from the PyETO library"
      },
      static: {
        description: "'Dummy' module with a static configurable delta"
      },
      passthrough: {
        description: "Passthrough module that returns the value of an Evapotranspiration sensor as delta"
      }
    },
    Ye = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Automatic duration calculation",
            description: "Calculation takes collected weather data up to that point and updates the bucket for each automatic zone. Then, the duration is adjusted based on the new bucket value and the collected weather data is removed.",
            labels: {
              "auto-calc-enabled": "Automatically calculate irrigation durations",
              "calc-time": "Calculate at"
            }
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Warning: weather data update time on or after calculation time"
            },
            header: "Automatic weather data update",
            description: "Collect and store weather data automatically. Weather data is required to calculate zone buckets and durations.",
            labels: {
              "auto-update-enabled": "Automatically update weather data",
              "auto-update-schedule": "Update schedule",
              "auto-update-time": "Update at",
              "auto-update-interval": "Update sensor data every",
              "auto-update-delay": "Update delay"
            },
            options: {
              minutes: "minutes",
              hours: "hours",
              days: "days"
            }
          },
          "automatic-clear": {
            header: "Automatic weather data pruning",
            description: "Automatically remove collected weather data at a configured time. Use this to make sure that there is no left over weather data from previous days. Don't remove the weather data before you calculate and only use this option if you expect the automatic update to collect weather data after you calculated for the day. Ideally, you want to prune as late in the day as possible.",
            labels: {
              "automatic-clear-enabled": "Automatically clear collected weather data",
              "automatic-clear-time": "Clear weather data at"
            }
          },
          continuousupdates: {
            header: "Continuous updates for sensors (experimental)",
            description: "This experimental feature will continuously update the sensor data. This is useful for sensor groups that use sources that provide continuous data, such as weather stations. This feature cannot be used for sensor groups that at least partly rely on weather services as continous polling of APIs will incur costs. Keep in mind that this is experimental and may not work as expected. Use at your own risk.",
            labels: {
              continuousupdates: "Enable continuous updates",
              sensor_debounce: "Sensor debounce"
            }
          }
        },
        description: "This page provides global settings.",
        title: "General",
        sections: {
          weather: "Weather",
          automation: "Automation",
          location: "Location",
          watering: "Watering behavior"
        }
      },
      schedules: {
        title: "Schedules",
        description: "Create recurring schedules to automatically calculate, update, or irrigate your zones. No automations needed.",
        add: "Add Schedule",
        no_items: "No schedules configured yet. Click 'Add Schedule' to get started.",
        zones_all: "All zones",
        zones_specific: "Specific zones",
        hours: "hours",
        minutes: "min",
        types: {
          daily: "Daily",
          weekly: "Weekly",
          monthly: "Monthly",
          interval: "Every N hours",
          sunrise: "Sunrise",
          sunset: "Sunset",
          solar_azimuth: "Solar azimuth"
        },
        actions: {
          calculate: "Calculate (update irrigation duration)",
          update: "Update (collect weather data)",
          irrigate: "Irrigate (run valves directly)"
        },
        days: {
          monday: "Mon",
          tuesday: "Tue",
          wednesday: "Wed",
          thursday: "Thu",
          friday: "Fri",
          saturday: "Sat",
          sunday: "Sun"
        },
        fields: {
          name: "Name",
          type: "Schedule type",
          enabled: "Enabled",
          time: "Time (HH:MM)",
          days_of_week: "Days of week",
          day_of_month: "Day of month",
          interval_hours: "Interval",
          action: "Action",
          zones: "Zones",
          start_date: "Start date (optional)",
          end_date: "End date (optional)",
          offset_minutes: "Offset from sunrise/sunset",
          account_for_duration: "Start early so irrigation finishes at trigger time",
          azimuth_angle: "Solar azimuth angle",
          time_anchor: "Time marks the"
        },
        dialog: {
          add_title: "Add Schedule",
          edit_title: "Edit Schedule"
        },
        time_anchor: {
          start: "Start of irrigation",
          finish: "End of irrigation"
        }
      },
      setup: {
        title: "Setup"
      },
      help: {
        title: "Help",
        cards: {
          "how-to-get-help": {
            title: "How to get help",
            "first-read-the": "First, read the",
            wiki: "Documentation",
            "if-you-still-need-help": "If you still need help reach out on the",
            "community-forum": "Community forum",
            "or-open-a": "or open a",
            "github-issue": "Github Issue",
            "english-only": "English only"
          }
        }
      },
      info: {
        title: "Info",
        description: "View information about next irrigation and system status.",
        "configuration-not-available": "Configuration not available.",
        cards: {
          "zone-bucket-values": {
            title: "Zone Bucket Values & Duration",
            labels: {
              bucket: "Bucket",
              duration: "Duration"
            },
            "no-zones": "No zones configured"
          },
          "next-irrigation": {
            title: "Next Irrigation",
            labels: {
              "next-start": "Next start",
              duration: "Duration",
              zones: "Zones"
            },
            "no-data": "No data available"
          },
          "irrigation-reason": {
            title: "Irrigation Reason",
            labels: {
              reason: "Reason",
              sunrise: "Sunrise",
              "total-duration": "Total duration",
              explanation: "Explanation"
            },
            "no-data": "No data available"
          },
          irrigate_now: {
            title: "Irrigate Now",
            description: "Immediately start irrigation for all zones that have a linked entity. Skip conditions are ignored.",
            button_all: "Run all zones now",
            no_linked_zones: "No zones have a linked switch/valve entity with a calculated duration."
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Add sensor group"
            },
            header: "Add sensor groups"
          },
          mapping: {
            aggregates: {
              average: "Average",
              first: "First",
              last: "Last",
              maximum: "Maximum",
              median: "Median",
              minimum: "Minimum",
              riemannsum: "Riemann sum",
              sum: "Sum",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "You cannot delete this sensor group because there is at least one zone using it.",
              invalid_source: "Invalid source",
              source_does_not_exist: "Source does not exist. Please enter a valid source, such as 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Dewpoint",
              evapotranspiration: "Evapotranspiration",
              humidity: "Humidity",
              "maximum temperature": "Maximum temperature",
              "minimum temperature": "Minimum temperature",
              precipitation: "Total precipitation",
              "current precipitation": "Current precipitation",
              pressure: "Pressure",
              "solar radiation": "Solar radiation",
              temperature: "Temperature",
              windspeed: "Wind speed"
            },
            pressure_types: {
              absolute: "absolute",
              relative: "relative"
            },
            "pressure-type": "Pressure is",
            "sensor-aggregate-of-sensor-values-to-calculate": "of sensor values to calculate duration",
            "sensor-aggregate-use-the": "Use the",
            "sensor-entity": "Sensor entity",
            static_value: "Value",
            "input-units": "Input provides values in",
            source: "Source",
            sources: {
              none: "None",
              weather_service: "Weather service",
              sensor: "Sensor",
              static: "Static value"
            }
          }
        },
        description: "Add one or more sensor groups that retrieve weather data from Weather service, from sensors or a combination of these. You can map each sensor group to one or more zones",
        labels: {
          "mapping-name": "Name"
        },
        no_items: "There are no sensor group defined yet.",
        title: "Sensor Groups",
        "weather-records": {
          title: "Weather Records",
          timestamp: "Time",
          temperature: "Temp",
          humidity: "Hum",
          dewpoint: "Dew",
          wind: "Wind",
          pressure: "Press",
          precipitation: "Precip",
          "retrieval-time": "Retrieved",
          "no-data": "No weather data available for this sensor group"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Add module"
            },
            header: "Add module"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "You cannot delete this module because there is at least one zone using it."
            },
            labels: {
              configuration: "Configuration",
              required: "indicates a required field"
            },
            "translated-options": {
              DontEstimate: "Do not estimate",
              EstimateFromSunHours: "Estimate from sun hours",
              EstimateFromTemp: "Estimate from temperature",
              EstimateFromSunHoursAndTemperature: "Estimate from average of sun hours and temperature"
            }
          }
        },
        description: "Add one or more modules that calculate irrigation duration. Each module comes with its own configuration and can be used to calculate duration for one or more zones.",
        no_items: "There are no modules defined yet.",
        title: "Modules"
      },
      zones: {
        actions: {
          add: "Add",
          calculate: "Calculate",
          information: "Information",
          update: "Update",
          "reset-bucket": "Reset bucket",
          "view-weather-info": "View weather data",
          "view-weather-info-message": "Weather data available for",
          "view-watering-calendar": "View watering calendar",
          irrigate_all: "Water all zones now",
          open_settings: "Edit settings"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Add zone"
            },
            header: "Add zone"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Recalculate durations",
              "update-all": "Refresh weather data",
              "reset-all-buckets": "Reset all buckets",
              "clear-all-weatherdata": "Clear all weather data"
            },
            header: "Actions on all zones"
          }
        },
        description: "Specify one or more irrigation zones here. The irrigation duration is calculated per zone, depending on size, throughput, state, module and sensor group.",
        labels: {
          bucket: "Bucket",
          duration: "Duration",
          "lead-time": "Lead time",
          mapping: "Sensor Group",
          "maximum-duration": "Maximum duration",
          multiplier: "Multiplier",
          name: "Name",
          size: "Size",
          state: "State",
          states: {
            automatic: "Automatic",
            disabled: "Disabled",
            manual: "Manual"
          },
          throughput: "Throughput",
          "maximum-bucket": "Maximum bucket",
          last_calculated: "Last calculated",
          "data-last-updated": "Data last updated",
          "data-number-of-data-points": "Number of data points",
          drainage_rate: "Drainage rate",
          linked_entity: "Linked switch/valve entity",
          linked_entity_placeholder: "e.g. switch.garden_valve",
          flow_sensor: "Flow meter sensor (optional)",
          flow_sensor_placeholder: "e.g. sensor.zone_flow_rate",
          irrigate_now: "Irrigate Now",
          bucket_threshold: "Minimum deficit to irrigate"
        },
        no_items: "There are no zones defined yet.",
        title: "Zones",
        status: {
          decision_disabled: "Turned off — this zone won't be watered automatically.",
          decision_water: "Watering needed: about {duration} on the next scheduled run.",
          decision_water_at: "Will water about {duration} at {time}.",
          decision_water_skip: "Deficit ~{duration}, but the next run will likely be skipped ({reason}).",
          decision_water_no_schedule: "Deficit ~{duration} — no schedule waters this zone; trigger it manually.",
          decision_no_water: "No watering needed right now — the soil has enough moisture.",
          decision_unknown: "Not calculated yet — press Update, then Calculate to check.",
          last_checked: "Last checked",
          never: "never",
          saved: "Saved",
          estimate_now: "Now",
          estimate_tag: "est.",
          estimate_method: {
            hourly: "Live estimate from hourly weather since the last calculation",
            proxy: "Estimate distributed from today's forecast since the last calculation"
          }
        },
        help: {
          bucket: "Soil-moisture balance. A negative value means the soil is dry and the zone needs water.",
          calculate: "Works out how long to water from the latest data. Run this after Update.",
          update: "Fetches the latest weather/sensor data for this zone.",
          irrigate_link_entity: "Link a switch/valve in this zone's settings to enable manual watering.",
          irrigate_all: "Opens the linked valves now for every zone with a deficit. Skip conditions (rain, wind, temperature) are ignored.",
          update_all: "Collects the latest weather/sensor data for all zones. Does not change durations on its own.",
          calculate_all: "Recomputes each automatic zone's watering duration from the data collected so far."
        },
        outlook: {
          next_run: "Next run",
          no_schedule: "No automatic schedule — zones water only when you trigger them.",
          setup_schedule: "Set up a schedule",
          targets_all: "all zones",
          targets_zones: "{count} zones",
          will_skip: "Next run will likely be skipped",
          will_run: "Conditions look clear for the next run.",
          why_skipped: "Why?",
          provisional: "forecast — may change",
          active_guards: "Active guards",
          last_run: "Last run",
          last_run_skipped: "skipped",
          last_run_ran: "ran",
          today: "today",
          tomorrow: "tomorrow",
          actions: {
            irrigate: "Water",
            calculate: "Recalculate",
            update: "Refresh data"
          },
          checks: {
            precipitation: "Rain forecast",
            days_between: "Days between watering",
            temperature: "Low temperature",
            wind: "High wind",
            rain_sensor: "Rain sensor"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} days",
            temperature: "{observed}° (below {threshold}°)",
            wind: "{observed} (above {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "No watering calendar data available for this zone.",
          error_prefix: "Error generating calendar:",
          month: "Month",
          et: "ET (mm)",
          precipitation: "Precipitation (mm)",
          watering: "Watering (L)",
          avg_temp: "Avg Temp (°C)",
          method_prefix: "Method:"
        },
        confirm_action: {
          reset_bucket_title: "Reset this zone's bucket?",
          reset_bucket_body: "This sets the bucket back to 0, discarding the accumulated moisture balance for this zone.",
          reset_all_buckets_title: "Reset all buckets?",
          reset_all_buckets_body: "This sets every zone's bucket back to 0, discarding the accumulated moisture balance. Watering calculations start fresh from the next update.",
          clear_weather_title: "Clear all weather data?",
          clear_weather_body: "This deletes all collected weather and sensor records for every zone. Zones will need fresh data before they can calculate again."
        },
        confirm_irrigate: {
          title: "Start irrigation?",
          body: "This opens the linked valve(s) now and bypasses all skip conditions (rain, temperature, minimum days between watering).",
          all_linked_zones: "All linked zones",
          toast_started: "Irrigation started",
          toast_failed: "Irrigation failed"
        }
      }
    },
    Je = "Smart Irrigation",
    Qe = {
      title: "Weather Service",
      description: "Configure which weather service to use for ET calculations and skip conditions.",
      enabled_label: "Enable weather service",
      service_label: "Weather service",
      api_key_label: "API key",
      api_key_placeholder: "Leave blank to keep existing key",
      api_key_configured: "API key is configured",
      api_key_not_configured: "No API key configured",
      api_key_help: "An API key from your chosen weather service provider. Open-Meteo does not require a key. OpenWeatherMap and Pirate Weather both offer free tiers.",
      no_api_key_needed: "Open-Meteo is a free service and requires no API key.",
      save_button: "Save weather settings",
      saved: "Weather settings saved",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather",
      openmeteo: "Open-Meteo (free, no key needed)",
      test_button: "Test Connection",
      test_button_testing: "Testing…",
      test_success: "✓ Connection successful",
      test_error_invalid_auth: "✗ Invalid API key — check that it is correct and active",
      test_error_cannot_connect: "✗ Cannot connect — check your internet connection",
      test_error_no_service: "✗ Select a weather service first",
      test_error_unknown: "✗ Test failed — unknown error"
    },
    et = {
      title: "Irrigation Start Triggers",
      description: "Configure when irrigation should start based on solar events. You can add multiple triggers for different schedules. For sunrise triggers, leaving offset at 0 will automatically use the total duration of all enabled zones.",
      add_trigger: "Add Trigger",
      edit_trigger: "Edit Trigger",
      delete_trigger: "Delete Trigger",
      trigger_types: {
        sunrise: "Sunrise",
        sunset: "Sunset",
        solar_azimuth: "Solar Azimuth"
      },
      fields: {
        name: {
          name: "Trigger Name",
          description: "A descriptive name to identify this trigger"
        },
        type: {
          name: "Trigger Type",
          description: "The type of solar event to trigger on"
        },
        enabled: {
          name: "Enabled",
          description: "Whether this trigger is currently active"
        },
        offset_minutes: {
          name: "Offset (minutes)",
          description: "Minutes before (-) or after (+) the solar event. For sunrise triggers, use 0 for automatic timing based on total zone duration."
        },
        azimuth_angle: {
          name: "Azimuth Angle (degrees)",
          description: "Solar azimuth angle in degrees where 0=North, 90=East, 180=South, 270=West"
        },
        account_for_duration: {
          name: "Account for Duration",
          description: "When enabled, irrigation will start early enough to finish at the specified time. When disabled, irrigation will start exactly at the specified time."
        }
      },
      dialog: {
        add_title: "Add Irrigation Start Trigger",
        edit_title: "Edit Irrigation Start Trigger",
        cancel: "Cancel",
        save: "Save",
        delete: "Delete"
      },
      no_triggers: "No irrigation start triggers configured. The system will use the default behavior (sunrise with total zone duration). Add triggers to customize when irrigation starts.",
      offset_auto: "Auto (calculated from total zone duration)",
      confirm_delete: "Are you sure you want to delete the trigger '{name}'?",
      validation: {
        name_required: "Trigger name is required",
        azimuth_invalid: "Azimuth angle must be a valid number"
      },
      help: {
        sunrise_offset: "For sunrise triggers: Use negative values to start before sunrise, positive to start after. Set to 0 to automatically start early enough to complete all zones before sunrise.",
        sunset_offset: "For sunset triggers: Use negative values to start before sunset, positive to start after sunset.",
        azimuth_explanation: "Solar azimuth is the compass direction of the sun. 0°=North, 90°=East, 180°=South, 270°=West. You can enter any angle value (e.g., 450° = 90°, -30° = 330°). Use this to trigger irrigation when the sun reaches a specific position.",
        multiple_triggers: "You can configure multiple triggers. Each enabled trigger will independently schedule irrigation starts."
      }
    },
    tt = {
      title: "Skip Conditions",
      description: "Automatically skip irrigation when conditions are unfavorable. Precipitation check requires a weather service. Temperature and wind checks also require a weather service.",
      threshold_label: "Precipitation Threshold",
      threshold_description: "Minimum total precipitation (in mm) forecast across the look-ahead window to skip irrigation.",
      lookahead_label: "Forecast look-ahead (days)",
      lookahead_help: "How many upcoming forecast days to add up when checking for rain. The forecast starts at tomorrow (today is excluded), so 1 = just the next day, 2 = the next two days, and so on.",
      temp_section_title: "Skip on low temperature",
      temp_threshold_label: "Skip if temperature is below",
      wind_section_title: "Skip on high wind speed",
      wind_threshold_label: "Skip if wind speed is above",
      rain_sensor_section_title: "Skip on rain sensor",
      rain_sensor_label: "Rain sensor entity (optional)",
      rain_sensor_placeholder: "e.g. binary_sensor.rain"
    },
    at = {
      title: "Location Coordinates",
      description: "Configure location coordinates for weather data retrieval. You can use manual coordinates different from your Home Assistant location if needed.",
      manual_enabled: "Use manual coordinates",
      use_ha_location: "Use Home Assistant location",
      latitude: "Latitude (decimal degrees)",
      longitude: "Longitude (decimal degrees)",
      elevation: "Elevation (meters above sea level)",
      current_ha_coords: "Current Home Assistant coordinates"
    },
    it = {
      title: "Days Between Irrigation",
      description: "Configure the minimum number of days that must pass between irrigation events. This helps control watering frequency for water conservation and plant health management.\n\nTypical real-world use cases:\n• Lawn care: 1-2 day intervals prevent overwatering\n• Drought restrictions: 6+ day intervals for weekly watering\n• Deep-rooted plants: 3-7 day intervals for less frequent watering\n• Water conservation: Customizable based on climate and soil conditions",
      label: "Minimum days between irrigation",
      help_text: "Set to 0 to disable this feature. Values from 1-365 days are supported. This setting works alongside existing precipitation forecasting logic."
    },
    nt = {
      title: "Zone Sequencing",
      description: "When multiple zones need irrigation, choose whether they run at the same time or one after another. Sequential mode waits for each zone to finish before starting the next. Rotating mode cycles through zones, giving each one a limited consecutive run before moving to the next.",
      parallel: "Parallel (all zones at once)",
      sequential: "Sequential (one zone at a time)",
      rotating: "Rotating (zones take turns)",
      max_consecutive_duration_label: "Max consecutive run time per zone",
      max_consecutive_duration_unit: "minutes",
      min_absorption_time_label: "Min. absorption time between slots",
      min_absorption_time_unit: "minutes (0 = disabled)"
    },
    rt = {
      zone_size: "The total irrigated area of this zone. Used with throughput to calculate how much water is applied per run.",
      zone_throughput: "Total water flow of your irrigation system for this zone (litres/min in metric, gal/min in imperial). Check your sprinkler datasheet or measure by timing how long it takes to fill a known container.",
      zone_drainage_rate: "How fast excess water drains from the soil when the bucket is full. Typical: lawn 50 mm/h, sandy soil 100+ mm/h, clay 10 mm/h.",
      zone_bucket: "Current water deficit (negative) or surplus (positive) for this zone. Irrigation triggers when bucket drops below the threshold.",
      zone_maximum_bucket: "Maximum moisture surplus the zone can hold. Water above this level is treated as runoff. Typical value: 50 mm.",
      zone_bucket_threshold: "Irrigation triggers when the bucket drops below this value. Must be 0 or negative. 0 means irrigate whenever there is any deficit.",
      zone_multiplier: "Scale factor applied to the calculated duration. Use above 1.0 to increase, below 1.0 to decrease. Useful for fine-tuning without changing physical measurements.",
      zone_lead_time: "Extra seconds added before irrigation starts. Use for pump warm-up or system pressurisation.",
      zone_maximum_duration: "Hard cap on any single irrigation run in seconds. Prevents runaway watering. Default: 3600 s (1 hour).",
      zone_linked_entity: "The HA switch or valve entity controlling water flow for this zone. This entity is turned on when irrigation runs.",
      zone_flow_sensor: "Optional sensor measuring actual water flow rate. Used for reporting only — does not affect duration calculations.",
      general_autoupdatedelay: "Seconds to wait after HA starts before the first weather data fetch. Allows other integrations to initialise first.",
      general_sensor_debounce: "Minimum gap in milliseconds between sensor readings to filter noise from rapidly changing sensors.",
      general_calctime: "Time of day when irrigation durations are recalculated from collected weather data. Format: HH:MM (24-hour).",
      general_cleardatatime: "Time of day when old weather data is purged. Must be set later than the calculation time.",
      general_days_between: "Minimum days between irrigation events for the same zone. Set to 0 to disable (irrigate whenever deficit exists).",
      general_autoupdateinterval: "How often weather data is collected. Choose a value that balances fresh data against API rate limits.",
      general_precipitation_threshold: "Irrigation is skipped if total forecast precipitation across the look-ahead window exceeds this amount.",
      general_temp_threshold: "Irrigation is skipped if the current temperature is below this value (e.g. to prevent frost damage).",
      general_wind_threshold: "Irrigation is skipped if wind speed exceeds this value (high winds reduce efficiency and cause drift)."
    },
    ot = {
      title: "Setup Wizard",
      open_button: "Setup Wizard",
      close: "Close",
      next: "Next",
      back: "Back",
      finish: "Finish",
      skip_step: "Skip this step",
      step_indicator: "Step {current} of {total}",
      stepper: {
        weather: "Weather",
        module: "Module",
        mapping: "Sensor Group",
        zone: "Zone"
      },
      setup_complete_banner: "Setup not complete. Run the wizard to get started.",
      open_wizard: "Open Wizard",
      steps: {
        welcome: {
          title: "Welcome to Smart Irrigation",
          intro: "This wizard guides you through the four steps needed to get your first zone irrigating automatically.",
          step1_label: "Weather Service — where to get weather data",
          step2_label: "Calculation Module — how irrigation duration is computed",
          step3_label: "Sensor Group — which data sources to use",
          step4_label: "Zone — your first irrigation zone",
          tip: "You can skip any step and configure it later from the Setup tab."
        },
        weather: {
          title: "Weather Service",
          description: "Choose how to get weather data. Open-Meteo is free and requires no API key — it is the easiest choice for most users."
        },
        module: {
          title: "Calculation Module",
          description: "A module calculates how long to irrigate based on evapotranspiration (ET). The PyETO module (FAO-56 method) is recommended for most users.",
          pick_label: "Select module type",
          no_modules: "No module types available."
        },
        mapping: {
          title: "Sensor Group",
          description: "A sensor group links each weather variable to a data source. Set the key variables below — you can refine individual sensor mappings later from the Setup → Sensor Groups tab.",
          name_label: "Sensor group name",
          source_label: "Data source for",
          use_weather_service: "Weather service",
          use_sensor: "Sensor",
          use_static: "Static value",
          use_none: "None / not used"
        },
        zone: {
          title: "First Zone",
          description: "A zone is one irrigation area (e.g. lawn, garden bed). Set the physical properties so the system can calculate the correct irrigation duration.",
          name_label: "Zone name",
          size_label: "Area",
          throughput_label: "Sprinkler throughput",
          entity_label: "Linked switch or valve",
          entity_placeholder: "e.g. switch.garden_valve",
          module_label: "Calculation module",
          mapping_label: "Sensor group"
        },
        done: {
          title: "Setup Complete!",
          description: "Your first zone is ready. Smart Irrigation will now calculate irrigation durations automatically based on weather data.",
          next_steps: "What you can do next:",
          tip1: "Go to Zones to view calculated durations and bucket values.",
          tip2: "Add more zones from the Zones tab.",
          tip3: "Refine all settings from the Setup tab.",
          go_zones: "Go to Zones",
          go_setup: "Go to Setup"
        }
      },
      confirm_close: {
        body: "Close the setup wizard? Your progress so far is saved.",
        keep: "Keep editing",
        close: "Close"
      }
    },
    st = {
      common: We,
      defaults: Ge,
      module: Ke,
      calcmodules: Xe,
      panels: Ye,
      title: Je,
      weather_service_config: Qe,
      irrigation_start_triggers: et,
      weather_skip: tt,
      coordinate_config: at,
      days_between_irrigation: it,
      zone_sequencing: nt,
      field_help: rt,
      wizard: ot
    },
    lt = Object.freeze({
      __proto__: null,
      common: We,
      defaults: Ge,
      module: Ke,
      calcmodules: Xe,
      panels: Ye,
      title: Je,
      weather_service_config: Qe,
      irrigation_start_triggers: et,
      weather_skip: tt,
      coordinate_config: at,
      days_between_irrigation: it,
      zone_sequencing: nt,
      field_help: rt,
      wizard: ot,
      default: st
    }),
    dt = {
      actions: {
        delete: "Eliminar",
        edit: "Editar",
        save: "Guardar",
        cancel: "Cancelar",
        confirm_delete: "Confirmar eliminación",
        confirm_delete_zone: "¿Seguro que quieres eliminar esta zona?"
      },
      labels: {
        module: "Módulo",
        no: "No",
        select: "Seleccionar",
        yes: "Sí",
        enabled: "Activado",
        disabled: "Desactivado",
        before: "antes",
        after: "después",
        settings: "Ajustes",
        bulk_actions: "Acciones masivas"
      },
      attributes: {
        size: "Tamaño",
        throughput: "Rendimiento",
        state: "Estado",
        bucket: "depósito",
        last_updated: "última actualización",
        last_calculated: "último cálculo",
        number_of_data_points: "número de puntos de datos"
      },
      loading: "Cargando",
      saving: "Guardando",
      units: {
        seconds: "segundos"
      },
      "loading-messages": {
        configuration: "Cargando configuración...",
        modules: "Cargando módulos...",
        general: "Cargando..."
      },
      "saving-messages": {
        adding: "Añadiendo...",
        saving: "Guardando..."
      },
      errors: {
        load_failed: "No se pudieron cargar los datos",
        save_failed: "No se pudieron guardar los cambios",
        delete_failed: "No se pudo eliminar",
        action_failed: "La acción falló"
      }
    },
    ut = {
      "default-zone": "Zona de riego predeterminada",
      "default-mapping": "Grupo de sensores predeterminado"
    },
    ct = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Nota: esta explicación utiliza '.' como separador decimal y muestra valores redondeados. El módulo devuelve una deficiencia de evapotranspiración de",
          "bucket-was": "El cubo era",
          "new-bucket-values-is": "El nuevo valor del cubo es",
          "old-bucket-variable": "old_bucket",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Dado que cubo < 0, el riego es necesario",
          "steps-taken-to-calculate-duration": "Para calcular la duración exacta, se siguieron los siguientes pasos",
          "precipitation-rate-defined-as": "La tasa de precipitación se define como",
          "duration-is-calculated-as": "La duración se calcula como",
          bucket: "cubo",
          "precipitation-rate-variable": "precipitation_rate",
          "multiplier-is-applied": "A continuación, se aplica el multiplicador. El multiplicador es",
          "duration-after-multiplier-is": "por lo que la duración es",
          "maximum-duration-is-applied": "A continuación, se aplica la duración máxima. La duración máxima es",
          "duration-after-maximum-duration-is": "por lo que la duración es",
          "lead-time-is-applied": "Por último, se aplica el plazo de entrega. El plazo de entrega es",
          "duration-after-lead-time-is": "por lo que la duración final es",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Como cubo >= 0, no es necesario regar y la duración se fija en",
          "maximum-bucket-is": "El tamaño máximo de cubo es",
          "max-bucket-variable": "max_bucket",
          drainage: "drenaje",
          "drainage-rate": "tasa de drenaje",
          hours: "horas",
          "drainage-rate-is": "La tasa de drenaje cuando está saturado (depósito al máximo) es",
          "current-drainage-is": "El drenaje actual se calcula como",
          "no-drainage": "El drenaje actual es 0 porque"
        }
      }
    },
    pt = {
      pyeto: {
        description: "Calcular la duración a partir del cálculo FAO56 de la biblioteca PyETO"
      },
      static: {
        description: "Módulo 'de prueba' con un delta estático configurable"
      },
      passthrough: {
        description: "Módulo de paso que devuelve el valor de un sensor de evapotranspiración como delta"
      }
    },
    mt = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Cálculo automático de la duración",
            labels: {
              "auto-calc-enabled": "Cálculo automático de la duración de las zonas",
              "auto-calc-time": "Calcular en",
              "calc-time": "Calcular a las"
            },
            description: "El cálculo toma los datos meteorológicos recopilados hasta ese momento y actualiza el depósito de cada zona automática. Después, la duración se ajusta según el nuevo valor del depósito y se eliminan los datos meteorológicos recopilados."
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Advertencia: la hora de actualización de los datos meteorológicos es igual o posterior a la hora de cálculo"
            },
            header: "Actualización automática de los datos meteorológicos",
            labels: {
              "auto-update-enabled": "Actualizar automáticamente los datos meteorológicos",
              "auto-update-first-update": "(Primer) Actualización a las",
              "auto-update-interval": "Actualizar datos del sensor cada",
              "auto-update-schedule": "Programa de actualización",
              "auto-update-time": "Actualizar a las",
              "auto-update-delay": "Retraso de actualización"
            },
            options: {
              days: "días",
              hours: "horas",
              minutes: "minutos"
            },
            description: "Recopila y almacena datos meteorológicos automáticamente. Los datos meteorológicos son necesarios para calcular los depósitos y las duraciones de las zonas."
          },
          "automatic-clear": {
            header: "Limpieza automática de datos meteorológicos",
            description: "Elimina automáticamente los datos meteorológicos recopilados a una hora configurada. Úsalo para asegurarte de que no queden datos meteorológicos de días anteriores. No elimines los datos meteorológicos antes de calcular y usa esta opción solo si esperas que la actualización automática recopile datos meteorológicos después de calcular para el día. Lo ideal es limpiar lo más tarde posible del día.",
            labels: {
              "automatic-clear-enabled": "Borrar automáticamente los datos meteorológicos recopilados",
              "automatic-clear-time": "Borrar datos meteorológicos a las"
            }
          },
          continuousupdates: {
            header: "Actualizaciones continuas de sensores (experimental)",
            description: "Función experimental para datos meteorológicos más detallados.",
            labels: {
              continuousupdates: "Activar actualizaciones continuas",
              sensor_debounce: "Antirrebote del sensor",
              "sensor-debounce": "Tiempo de antirrebote del sensor (ms)"
            }
          }
        },
        description: "Esta página provee configuraciones globales.",
        title: "General",
        sections: {
          weather: "Meteorología",
          automation: "Automatización",
          location: "Ubicación",
          watering: "Comportamiento de riego"
        }
      },
      help: {
        title: "Ayuda",
        cards: {
          "how-to-get-help": {
            title: "Cómo obtener ayuda",
            "first-read-the": "Primero lee la",
            wiki: "Documentación",
            "if-you-still-need-help": "Si aún necesitas ayuda, puedes:",
            "community-forum": "Comunidad/Foro",
            "or-open-a": "o abrir un",
            "github-issue": "Incidencia en GitHub",
            "english-only": "sólo en inglés"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Añadir grupo de sensores"
            },
            header: "Añadir grupos de sensores"
          },
          mapping: {
            aggregates: {
              average: "Promedio",
              first: "Primero",
              last: "Último",
              maximum: "Máximo",
              median: "Mediana",
              minimum: "Mínimo",
              sum: "Suma",
              riemannsum: "Suma de Riemann",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "No puedes eliminar este grupo de sensores porque hay al menos una zona que lo está usando.",
              invalid_source: "Origen no válido",
              source_does_not_exist: "El origen no existe. Introduce un origen válido, como 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Punto de rocío",
              evapotranspiration: "Evapotranspiración",
              humidity: "Humedad",
              "maximum temperature": "Temperatura máxima",
              "minimum temperature": "Temperatura mínima",
              precipitation: "Precipitación total",
              pressure: "Presión",
              "solar radiation": "Radiación solar",
              temperature: "Temperatura",
              windspeed: "Velocidad del viento",
              "current precipitation": "Precipitación actual"
            },
            "sensor-aggregate-of-sensor-values-to-calculate": "de los valores de los sensores para calcular la duración",
            "sensor-aggregate-use-the": "Usar la",
            "sensor-entity": "Entidad de sensor",
            static_value: "Valor estático",
            "input-units": "Unidades de entrada",
            source: "Fuente",
            sources: {
              none: "Ninguno",
              weather_service: "Servicio meteorológico",
              sensor: "Sensor",
              static: "Valor estático"
            },
            pressure_types: {
              absolute: "absoluta",
              relative: "relativa"
            },
            "pressure-type": "La presión es"
          }
        },
        description: "Añada uno o más grupos de sensores que recuperen datos meteorológicos de Weather service, de sensores o de una combinación de éstos. Puede asignar cada grupo de sensores a una o más zonas",
        labels: {
          "mapping-name": "Nombre del grupo de sensores"
        },
        no_items: "Aún no hay grupos de sensores definidos.",
        title: "Grupos de sensores",
        "weather-records": {
          title: "Registros meteorológicos",
          timestamp: "Hora",
          temperature: "Temp.",
          humidity: "Humidity",
          precipitation: "Precip.",
          "retrieval-time": "Obtenido",
          "no-data": "No hay datos meteorológicos disponibles para este grupo de sensores",
          dewpoint: "Rocío",
          wind: "Viento",
          pressure: "Presión"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Añadir módulo"
            },
            header: "Añadir módulo"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "No puedes eliminar este módulo porque hay al menos una zona que lo está usando."
            },
            labels: {
              configuration: "Configuración",
              required: "Requerido"
            },
            "translated-options": {
              DontEstimate: "No estimar",
              EstimateFromSunHours: "Estimar desde horas de sol",
              EstimateFromTemp: "Estimar desde temperatura",
              EstimateFromSunHoursAndTemperature: "Estimar a partir del promedio de horas de sol y temperatura"
            }
          }
        },
        description: "Añada uno o varios módulos que calculen la duración del riego. Cada módulo tiene su propia configuración y puede utilizarse para calcular la duración de una o varias zonas.",
        no_items: "Aún no hay módulos definidos.",
        title: "Módulos"
      },
      zones: {
        actions: {
          add: "Añadir",
          calculate: "Calcular",
          information: "Información",
          update: "Actualizar",
          "reset-bucket": "Resetear cubo",
          "view-weather-info": "Ver datos meteorológicos",
          "view-weather-info-message": "Datos meteorológicos disponibles para",
          "view-watering-calendar": "Calendario de riego",
          irrigate_all: "Regar todas las zonas ahora",
          open_settings: "Editar ajustes"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Añadir zona"
            },
            header: "Añadir zona"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Recalcular duraciones",
              "update-all": "Actualizar datos meteorológicos",
              "reset-all-buckets": "Resetear todos los cubos",
              "clear-all-weatherdata": "Borrar todos los datos meteorológicos"
            },
            header: "Acciones en todas las zonas"
          }
        },
        description: "Especifique aquí una o varias zonas de riego. La duración del riego se calcula por zona, en función del tamaño, el rendimiento, el estado, el módulo y el grupo de sensores.",
        labels: {
          bucket: "Cubo",
          duration: "Duración",
          "lead-time": "Tiempo de espera",
          mapping: "Grupo de sensores",
          "maximum-duration": "Duración máxima",
          multiplier: "Multiplicador",
          name: "Nombre",
          size: "Tamaño",
          state: "Estado",
          states: {
            automatic: "Automático",
            disabled: "Desactivado",
            manual: "Manual"
          },
          throughput: "Rendimiento",
          "maximum-bucket": "Cubo máximo",
          last_calculated: "Último cálculo",
          "data-last-updated": "Datos actualizados por última vez",
          "data-number-of-data-points": "Número de puntos de datos",
          drainage_rate: "Tasa de drenaje",
          linked_entity: "Entidad de interruptor/válvula vinculada",
          linked_entity_placeholder: "p.ej. switch.valvula_jardin",
          irrigate_now: "Regar ahora",
          bucket_threshold: "Déficit mínimo para regar",
          flow_sensor: "Sensor de caudalímetro (opcional)",
          flow_sensor_placeholder: "p. ej. sensor.zone_flow_rate"
        },
        no_items: "Aún no hay zonas definidas.",
        title: "Zonas",
        confirm_irrigate: {
          title: "¿Iniciar el riego?",
          body: "Esto abrirá ahora las válvulas vinculadas e ignora todas las condiciones de exclusión (lluvia, temperatura, días mínimos entre riegos).",
          all_linked_zones: "Todas las zonas vinculadas",
          toast_started: "Riego iniciado",
          toast_failed: "Error en el riego"
        },
        status: {
          decision_disabled: "Desactivada — esta zona no se regará automáticamente.",
          decision_water: "Riego necesario: unos {duration} en el próximo riego programado.",
          decision_water_at: "Regará unos {duration} a las {time}.",
          decision_water_skip: "Déficit ~{duration}, pero el próximo riego probablemente se omitirá ({reason}).",
          decision_water_no_schedule: "Déficit ~{duration} — ningún horario riega esta zona; actívala manualmente.",
          decision_no_water: "No se necesita riego ahora mismo — el suelo tiene suficiente humedad.",
          decision_unknown: "Aún sin calcular — pulsa Actualizar y luego Calcular para comprobar.",
          last_checked: "Última comprobación",
          never: "nunca",
          saved: "Guardado",
          estimate_now: "Ahora",
          estimate_tag: "est.",
          estimate_method: {
            hourly: "Estimación en vivo del tiempo horario desde el último cálculo",
            proxy: "Estimación distribuida de la previsión de hoy desde el último cálculo"
          }
        },
        help: {
          bucket: "Balance de humedad del suelo (cubo). Un valor negativo significa que el suelo está seco y la zona necesita agua.",
          calculate: "Calcula cuánto tiempo regar a partir de los últimos datos. Ejecútalo después de Actualizar.",
          update: "Obtiene los últimos datos meteorológicos/de sensores de esta zona.",
          irrigate_link_entity: "Vincula un interruptor/válvula en los ajustes de esta zona para permitir el riego manual.",
          irrigate_all: "Abre ahora las válvulas vinculadas de cada zona con déficit. Se ignoran las condiciones de exclusión (lluvia, viento, temperatura).",
          update_all: "Recoge los últimos datos meteorológicos/de sensores de todas las zonas. No cambia las duraciones por sí solo.",
          calculate_all: "Recalcula la duración de riego de cada zona automática a partir de los datos recogidos hasta ahora."
        },
        outlook: {
          next_run: "Próximo riego",
          no_schedule: "Sin horario automático — las zonas solo se riegan cuando lo activas tú.",
          setup_schedule: "Configurar un horario",
          targets_all: "todas las zonas",
          targets_zones: "{count} zonas",
          will_skip: "El próximo riego probablemente se omitirá",
          will_run: "Las condiciones parecen despejadas para el próximo riego.",
          why_skipped: "¿Por qué?",
          provisional: "previsión — puede cambiar",
          active_guards: "Condiciones activas",
          last_run: "Último riego",
          last_run_skipped: "omitido",
          last_run_ran: "ejecutado",
          today: "hoy",
          tomorrow: "mañana",
          actions: {
            irrigate: "Regar",
            calculate: "Recalcular",
            update: "Actualizar datos"
          },
          checks: {
            precipitation: "Lluvia prevista",
            days_between: "Días entre riegos",
            temperature: "Temperatura baja",
            wind: "Viento fuerte",
            rain_sensor: "Sensor de lluvia"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} días",
            temperature: "{observed}° (por debajo de {threshold}°)",
            wind: "{observed} (por encima de {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "No hay datos de calendario de riego disponibles para esta zona.",
          error_prefix: "Error al generar el calendario:",
          month: "Mes",
          et: "ET (mm)",
          precipitation: "Precipitación (mm)",
          watering: "Riego (L)",
          avg_temp: "Temp. media (°C)",
          method_prefix: "Método:"
        },
        confirm_action: {
          reset_bucket_title: "¿Restablecer el cubo de esta zona?",
          reset_bucket_body: "Esto restablece el cubo a 0, descartando el balance de humedad acumulado de esta zona.",
          reset_all_buckets_title: "¿Restablecer todos los cubos?",
          reset_all_buckets_body: "Esto restablece a 0 el cubo de cada zona, descartando el balance de humedad acumulado. Los cálculos de riego empezarán de nuevo en la próxima actualización.",
          clear_weather_title: "¿Borrar todos los datos meteorológicos?",
          clear_weather_body: "Esto elimina todos los registros meteorológicos y de sensores de todas las zonas. Las zonas necesitarán datos nuevos antes de poder calcular de nuevo."
        }
      },
      schedules: {
        title: "Programas",
        description: "Cree programas recurrentes para calcular, actualizar o regar automáticamente — sin automatizaciones.",
        add: "Añadir programa",
        no_items: "Aún no hay programas configurados. Haga clic en 'Añadir programa'.",
        zones_all: "Todas las zonas",
        zones_specific: "Zonas específicas",
        hours: "horas",
        minutes: "min",
        types: {
          daily: "Diario",
          weekly: "Semanal",
          monthly: "Mensual",
          interval: "Cada N horas",
          sunrise: "Amanecer",
          sunset: "Atardecer",
          solar_azimuth: "Azimut solar"
        },
        actions: {
          calculate: "Calcular (actualizar duración de riego)",
          update: "Actualizar (recopilar datos meteorológicos)",
          irrigate: "Regar (controlar válvulas directamente)"
        },
        days: {
          monday: "Lu",
          tuesday: "Ma",
          wednesday: "Mi",
          thursday: "Ju",
          friday: "Vi",
          saturday: "Sá",
          sunday: "Do"
        },
        fields: {
          name: "Nombre",
          type: "Tipo de programa",
          enabled: "Activado",
          time: "Hora (HH:MM)",
          days_of_week: "Días de la semana",
          day_of_month: "Día del mes",
          interval_hours: "Intervalo",
          action: "Acción",
          zones: "Zonas",
          start_date: "Fecha de inicio (opcional)",
          end_date: "Fecha de fin (opcional)",
          offset_minutes: "Desplazamiento desde amanecer/atardecer",
          account_for_duration: "Iniciar antes para que el riego termine a la hora objetivo",
          azimuth_angle: "Ángulo de azimut solar",
          time_anchor: "La hora marca el"
        },
        dialog: {
          add_title: "Añadir programa",
          edit_title: "Editar programa"
        },
        time_anchor: {
          start: "Inicio del riego",
          finish: "Fin del riego"
        }
      },
      info: {
        title: "Información",
        description: "Ver información sobre el próximo riego y el estado del sistema.",
        "configuration-not-available": "Configuración no disponible.",
        cards: {
          "zone-bucket-values": {
            title: "Valores de depósito y duración",
            labels: {
              bucket: "Depósito",
              duration: "Duración"
            },
            "no-zones": "No hay zonas configuradas"
          },
          "next-irrigation": {
            title: "Próximo riego",
            labels: {
              "next-start": "Próximo inicio",
              duration: "Duración",
              zones: "Zonas"
            },
            "no-data": "No hay datos disponibles"
          },
          "irrigation-reason": {
            title: "Motivo del riego",
            labels: {
              reason: "Razón",
              sunrise: "Amanecer",
              "total-duration": "Duración total",
              explanation: "Explicación"
            },
            "no-data": "No hay datos disponibles"
          },
          irrigate_now: {
            title: "Regar ahora",
            description: "Iniciar riego inmediatamente para todas las zonas con entidad vinculada. Las condiciones de omisión se ignoran.",
            button_all: "Iniciar todas las zonas ahora",
            no_linked_zones: "Ninguna zona tiene una entidad de interruptor/válvula vinculada con duración calculada."
          }
        }
      },
      setup: {
        title: "Configuración"
      }
    },
    gt = "Smart Irrigation",
    ht = {
      title: "Coordenadas de Ubicación",
      description: "Configure las coordenadas de ubicación para obtener datos meteorológicos. Puede usar coordenadas manuales diferentes a la ubicación de Home Assistant si es necesario.",
      manual_enabled: "Usar coordenadas manuales",
      use_ha_location: "Usar ubicación de Home Assistant",
      latitude: "Latitud (grados decimales)",
      longitude: "Longitud (grados decimales)",
      elevation: "Elevación (metros sobre el nivel del mar)",
      current_ha_coords: "Coordenadas actuales de Home Assistant"
    },
    vt = {
      title: "Días entre riegos",
      description: "Configure el número mínimo de días entre eventos de riego.",
      label: "Días mínimos entre riegos",
      help_text: "Establezca 0 para desactivar. Se admiten valores de 1 a 365 días."
    },
    _t = {
      title: "Disparadores de inicio de riego",
      description: "Configura cuándo debe iniciarse el riego según eventos solares. Puedes añadir varios disparadores para diferentes horarios. Para los disparadores de amanecer, dejar el desfase en 0 usará automáticamente la duración total de todas las zonas activadas.",
      add_trigger: "Añadir disparador",
      edit_trigger: "Editar disparador",
      delete_trigger: "Eliminar disparador",
      trigger_types: {
        sunrise: "Amanecer",
        sunset: "Atardecer",
        solar_azimuth: "Acimut solar"
      },
      fields: {
        name: {
          name: "Nombre del disparador",
          description: "Un nombre descriptivo para identificar este disparador"
        },
        type: {
          name: "Tipo de disparador",
          description: "El tipo de evento solar con el que activar"
        },
        enabled: {
          name: "Activado",
          description: "Si este disparador está actualmente activo"
        },
        offset_minutes: {
          name: "Desfase (minutos)",
          description: "Minutos antes (-) o después (+) del evento solar. Para los disparadores de amanecer, usa 0 para una temporización automática basada en la duración total de las zonas."
        },
        azimuth_angle: {
          name: "Ángulo de acimut (grados)",
          description: "Ángulo de acimut solar en grados donde 0=Norte, 90=Este, 180=Sur, 270=Oeste"
        },
        account_for_duration: {
          name: "Tener en cuenta la duración",
          description: "Si está activado, el riego comenzará con suficiente antelación para terminar a la hora indicada. Si está desactivado, el riego comenzará exactamente a la hora indicada."
        }
      },
      dialog: {
        add_title: "Añadir disparador de inicio de riego",
        edit_title: "Editar disparador de inicio de riego",
        cancel: "Cancelar",
        save: "Guardar",
        delete: "Eliminar"
      },
      no_triggers: "No hay disparadores de inicio de riego configurados. El sistema usará el comportamiento predeterminado (amanecer con la duración total de las zonas). Añade disparadores para personalizar cuándo comienza el riego.",
      offset_auto: "Automático (calculado a partir de la duración total de las zonas)",
      confirm_delete: "¿Seguro que quieres eliminar el disparador '{name}'?",
      validation: {
        name_required: "El nombre del disparador es obligatorio",
        azimuth_invalid: "El ángulo de acimut debe ser un número válido"
      },
      help: {
        sunrise_offset: "Para los disparadores de amanecer: usa valores negativos para empezar antes del amanecer, positivos para empezar después. Pon 0 para empezar automáticamente con tiempo suficiente para completar todas las zonas antes del amanecer.",
        sunset_offset: "Para los disparadores de atardecer: usa valores negativos para empezar antes del atardecer, positivos para empezar después del atardecer.",
        azimuth_explanation: "El acimut solar es la dirección de la brújula del sol. 0°=Norte, 90°=Este, 180°=Sur, 270°=Oeste. Puedes introducir cualquier valor de ángulo (p. ej., 450° = 90°, -30° = 330°). Úsalo para activar el riego cuando el sol alcance una posición concreta.",
        multiple_triggers: "Puedes configurar varios disparadores. Cada disparador activado programará los inicios de riego de forma independiente."
      }
    },
    bt = {
      title: "Condiciones de omisión",
      description: "Omitir automáticamente el riego cuando las condiciones sean desfavorables. Las comprobaciones de precipitación, temperatura y viento requieren un servicio meteorológico.",
      threshold_label: "Umbral de precipitación",
      threshold_description: "Precipitación total mínima prevista (en mm) en la ventana de previsión para omitir el riego.",
      lookahead_label: "Ventana de previsión (días)",
      lookahead_help: "Cuántos días de previsión próximos se suman al comprobar la lluvia. La previsión empieza mañana (hoy se excluye), así que 1 = solo el día siguiente, 2 = los próximos dos días, etc.",
      temp_section_title: "Omitir por temperatura baja",
      temp_threshold_label: "Omitir si temperatura por debajo de",
      wind_section_title: "Omitir por viento fuerte",
      wind_threshold_label: "Omitir si velocidad del viento superior a",
      rain_sensor_section_title: "Condición del sensor de lluvia",
      rain_sensor_label: "Entidad del sensor de lluvia (opcional)",
      rain_sensor_placeholder: "p.ej. binary_sensor.lluvia"
    },
    ft = {
      title: "Secuencia de zonas",
      description: "Cuando varias zonas necesitan riego, elija si se ejecutan al mismo tiempo o una tras otra. En modo secuencial, el sistema espera a que cada zona termine antes de iniciar la siguiente.",
      parallel: "Paralelo (todas las zonas a la vez)",
      sequential: "Secuencial (una zona a la vez)",
      rotating: "Rotativo (las zonas se turnan)",
      max_consecutive_duration_label: "Tiempo máx. de ejecución consecutiva por zona",
      max_consecutive_duration_unit: "minutos",
      min_absorption_time_label: "Tiempo mín. de absorción entre turnos",
      min_absorption_time_unit: "minutos (0 = desactivado)"
    },
    kt = {
      title: "Servicio meteorológico",
      description: "Configura qué servicio meteorológico usar para los cálculos de ET y las condiciones de omisión.",
      enabled_label: "Activar servicio meteorológico",
      service_label: "Servicio meteorológico",
      api_key_label: "Clave API",
      api_key_placeholder: "Déjalo en blanco para conservar la clave existente",
      api_key_configured: "La clave API está configurada",
      api_key_not_configured: "No hay clave API configurada",
      api_key_help: "Una clave API de tu proveedor de servicio meteorológico elegido. Open-Meteo no requiere clave. OpenWeatherMap y Pirate Weather ofrecen niveles gratuitos.",
      no_api_key_needed: "Open-Meteo es un servicio gratuito y no requiere clave API.",
      save_button: "Guardar ajustes meteorológicos",
      saved: "Ajustes meteorológicos guardados",
      openmeteo: "Open-Meteo (gratis, sin clave)",
      test_button: "Probar conexión",
      test_button_testing: "Probando…",
      test_success: "✓ Conexión correcta",
      test_error_invalid_auth: "✗ Clave API no válida — comprueba que sea correcta y esté activa",
      test_error_cannot_connect: "✗ No se puede conectar — comprueba tu conexión a internet",
      test_error_no_service: "✗ Selecciona primero un servicio meteorológico",
      test_error_unknown: "✗ Prueba fallida — error desconocido",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    zt = {
      zone_size: "La superficie total regada de esta zona. Se usa junto con el caudal para calcular cuánta agua se aplica por ciclo.",
      zone_throughput: "Flujo total de agua de tu sistema de riego para esta zona (litros/min en métrico, gal/min en imperial). Consulta la ficha técnica de tus aspersores o mídelo cronometrando cuánto tarda en llenarse un recipiente conocido.",
      zone_drainage_rate: "La rapidez con que el agua sobrante drena del suelo cuando el depósito está lleno. Típico: césped 50 mm/h, suelo arenoso 100+ mm/h, arcilla 10 mm/h.",
      zone_bucket: "Déficit (negativo) o superávit (positivo) de agua actual de esta zona. El riego se activa cuando el depósito cae por debajo del umbral.",
      zone_maximum_bucket: "Superávit máximo de humedad que la zona puede retener. El agua por encima de este nivel se trata como escorrentía. Valor típico: 50 mm.",
      zone_bucket_threshold: "El riego se activa cuando el depósito cae por debajo de este valor. Debe ser 0 o negativo. 0 significa regar siempre que haya déficit.",
      zone_multiplier: "Factor de escala aplicado a la duración calculada. Por encima de 1,0 aumenta, por debajo de 1,0 disminuye. Útil para ajustar sin cambiar las mediciones físicas.",
      zone_lead_time: "Segundos adicionales antes de que comience el riego. Úsalo para el calentamiento de la bomba o la presurización del sistema.",
      zone_maximum_duration: "Límite máximo absoluto para cualquier ciclo de riego individual en segundos. Evita el riego descontrolado. Predeterminado: 3600 s (1 hora).",
      zone_linked_entity: "La entidad de interruptor o válvula de HA que controla el flujo de agua de esta zona. Esta entidad se activa cuando se ejecuta el riego.",
      zone_flow_sensor: "Sensor opcional que mide el caudal real. Se usa solo para informes — no afecta a los cálculos de duración.",
      general_autoupdatedelay: "Segundos a esperar tras iniciar HA antes de la primera obtención de datos meteorológicos. Permite que otras integraciones se inicialicen primero.",
      general_sensor_debounce: "Intervalo mínimo en milisegundos entre lecturas del sensor para filtrar el ruido de sensores que cambian rápidamente.",
      general_calctime: "Hora del día en que se recalculan las duraciones de riego a partir de los datos meteorológicos recopilados. Formato: HH:MM (24 horas).",
      general_cleardatatime: "Hora del día en que se purgan los datos meteorológicos antiguos. Debe ser posterior a la hora de cálculo.",
      general_days_between: "Días mínimos entre eventos de riego para la misma zona. Pon 0 para desactivar (regar siempre que haya déficit).",
      general_autoupdateinterval: "Con qué frecuencia se recopilan los datos meteorológicos. Elige un valor que equilibre datos frescos con los límites de la API.",
      general_precipitation_threshold: "El riego se omite si la precipitación total prevista en la ventana de previsión supera esta cantidad.",
      general_temp_threshold: "El riego se omite si la temperatura actual es inferior a este valor (p. ej. para evitar daños por heladas).",
      general_wind_threshold: "El riego se omite si la velocidad del viento supera este valor (el viento fuerte reduce la eficiencia y causa deriva)."
    },
    yt = {
      title: "Asistente de configuración",
      open_button: "Asistente de configuración",
      close: "Cerrar",
      next: "Siguiente",
      back: "Atrás",
      finish: "Finalizar",
      skip_step: "Omitir este paso",
      step_indicator: "Paso {current} de {total}",
      setup_complete_banner: "Configuración incompleta. Ejecuta el asistente para empezar.",
      open_wizard: "Abrir asistente",
      steps: {
        welcome: {
          title: "Bienvenido a Smart Irrigation",
          intro: "Este asistente te guía por los cuatro pasos necesarios para que tu primera zona riegue automáticamente.",
          step1_label: "Servicio meteorológico — de dónde obtener los datos meteorológicos",
          step2_label: "Módulo de cálculo — cómo se calcula la duración del riego",
          step3_label: "Grupo de sensores — qué fuentes de datos usar",
          step4_label: "Zona — tu primera zona de riego",
          tip: "Puedes omitir cualquier paso y configurarlo más tarde desde la pestaña Configuración."
        },
        weather: {
          title: "Servicio meteorológico",
          description: "Elige cómo obtener los datos meteorológicos. Open-Meteo es gratuito y no requiere clave API — es la opción más sencilla para la mayoría."
        },
        module: {
          title: "Módulo de cálculo",
          description: "Un módulo calcula cuánto regar según la evapotranspiración (ET). El módulo PyETO (método FAO-56) es el recomendado para la mayoría.",
          pick_label: "Seleccionar tipo de módulo",
          no_modules: "No hay tipos de módulo disponibles."
        },
        mapping: {
          title: "Grupo de sensores",
          description: "Un grupo de sensores vincula cada variable meteorológica con una fuente de datos. Define las variables clave a continuación — podrás refinar las asignaciones de sensores individuales más tarde en la pestaña Configuración → Grupos de sensores.",
          name_label: "Nombre del grupo de sensores",
          source_label: "Fuente de datos para",
          use_weather_service: "Servicio meteorológico",
          use_sensor: "Sensor",
          use_static: "Valor estático",
          use_none: "Ninguna / sin usar"
        },
        zone: {
          title: "Primera zona",
          description: "Una zona es un área de riego (p. ej. césped, parterre). Define las propiedades físicas para que el sistema pueda calcular la duración de riego correcta.",
          name_label: "Nombre de la zona",
          size_label: "Superficie",
          throughput_label: "Caudal del aspersor",
          entity_label: "Interruptor o válvula vinculados",
          entity_placeholder: "p. ej. switch.garden_valve",
          module_label: "Módulo de cálculo",
          mapping_label: "Grupo de sensores"
        },
        done: {
          title: "¡Configuración completada!",
          description: "Tu primera zona está lista. Smart Irrigation ahora calculará las duraciones de riego automáticamente según los datos meteorológicos.",
          next_steps: "Qué puedes hacer a continuación:",
          tip1: "Ve a Zonas para ver las duraciones calculadas y los valores del depósito.",
          tip2: "Añade más zonas desde la pestaña Zonas.",
          tip3: "Ajusta todos los parámetros desde la pestaña Configuración.",
          go_zones: "Ir a Zonas",
          go_setup: "Ir a Configuración"
        }
      },
      stepper: {
        weather: "Meteorología",
        module: "Módulo",
        mapping: "Grupo de sensores",
        zone: "Zona"
      },
      confirm_close: {
        body: "¿Cerrar el asistente de configuración? Tu progreso se ha guardado.",
        keep: "Seguir editando",
        close: "Cerrar"
      }
    },
    wt = {
      common: dt,
      defaults: ut,
      module: ct,
      calcmodules: pt,
      panels: mt,
      title: gt,
      coordinate_config: ht,
      days_between_irrigation: vt,
      irrigation_start_triggers: _t,
      weather_skip: bt,
      zone_sequencing: ft,
      weather_service_config: kt,
      field_help: zt,
      wizard: yt
    },
    At = Object.freeze({
      __proto__: null,
      common: dt,
      defaults: ut,
      module: ct,
      calcmodules: pt,
      panels: mt,
      title: gt,
      coordinate_config: ht,
      days_between_irrigation: vt,
      irrigation_start_triggers: _t,
      weather_skip: bt,
      zone_sequencing: ft,
      weather_service_config: kt,
      field_help: zt,
      wizard: yt,
      default: wt
    }),
    St = {
      actions: {
        delete: "Suppression",
        edit: "Modifier",
        save: "Enregistrer",
        cancel: "Annuler",
        confirm_delete: "Confirmer la suppression",
        confirm_delete_zone: "Voulez-vous vraiment supprimer cette zone ?"
      },
      labels: {
        module: "Module",
        no: "Non",
        select: "Sélectionner",
        yes: "Oui",
        enabled: "Activé",
        disabled: "Désactivé",
        before: "avant",
        after: "après",
        settings: "Paramètres",
        bulk_actions: "Actions groupées"
      },
      attributes: {
        size: "taille",
        throughput: "débit",
        state: "état",
        bucket: "réservoir",
        last_updated: "dernière mise à jour",
        last_calculated: "dernier calcul",
        number_of_data_points: "nombre de points de données"
      },
      loading: "Chargement",
      saving: "Enregistrement",
      units: {
        seconds: "secondes"
      },
      "loading-messages": {
        configuration: "Chargement de la configuration...",
        modules: "Chargement des modules...",
        general: "Chargement..."
      },
      "saving-messages": {
        adding: "Ajout...",
        saving: "Enregistrement..."
      },
      errors: {
        load_failed: "Impossible de charger les données",
        save_failed: "Impossible d'enregistrer les modifications",
        delete_failed: "Impossible de supprimer",
        action_failed: "Échec de l'action"
      }
    },
    Et = {
      "default-zone": "Zone par défaut",
      "default-mapping": "Groupe de capteurs par défaut"
    },
    xt = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "NB: cette explication utilise '.' comme séparateur décimal, et affiche des valeurs arrondies. Le module a donné un manque d'Évapotranspiration de",
          "bucket-was": "Le seau (bucket) était de",
          "new-bucket-values-is": "La nouvelle valeur du seau (bucket) est",
          "old-bucket-variable": "ancien_bucket",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Puisque le seau (bucket) est < 0, l'irrigation est nécessaire",
          "steps-taken-to-calculate-duration": "Pour calculer la durée d'irrigation, les étapes suivantes ont été réalisées",
          "precipitation-rate-defined-as": "Le taux de précipitation est défini comme",
          "duration-is-calculated-as": "La durée d'irrigation est calculée avec",
          bucket: "seau (bucket)",
          "precipitation-rate-variable": "taux_precipitation",
          "multiplier-is-applied": "Le multiplicateur est appliqué. Le multiplicateur est",
          "duration-after-multiplier-is": "donc la durée d'irrigation est de",
          "maximum-duration-is-applied": "Ensuite la durée maximale est appliquée. La durée maximale est de",
          "duration-after-maximum-duration-is": "donc la durée d'irrigation est de",
          "lead-time-is-applied": "Enfin, le délai est appliqué. Le délai est de",
          "duration-after-lead-time-is": "et donc la durée finale est de",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Puisque le seau (bucket) est >= 0, l'irrigation n'est pas nécessaire, et la durée est réglée à",
          "maximum-bucket-is": "la taille du seau (bucket) maximale est",
          "max-bucket-variable": "max_bucket",
          drainage: "drainage",
          "drainage-rate": "taux de drainage",
          hours: "heures",
          "drainage-rate-is": "Le taux de drainage à saturation (réservoir au maximum) est",
          "current-drainage-is": "Le drainage actuel est calculé comme",
          "no-drainage": "Le drainage actuel est 0 parce que"
        }
      }
    },
    Tt = {
      pyeto: {
        description: "Le calcul de durée est basée sur le calcul FAO56 de la bibliothèque PyETO"
      },
      static: {
        description: "Module 'Dummy' avec un delta statique configurable"
      },
      passthrough: {
        description: "Module passerelle qui renvoie la valeur d'un capteur d'Évapotranspiration comme delta"
      }
    },
    jt = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Calcul automatique de la durée",
            labels: {
              "auto-calc-enabled": "Calcule automatiquement la durée par zone",
              "auto-calc-time": "Calcule à",
              "calc-time": "Calculer à"
            },
            description: "Le calcul prend en compte les données météo jusqu'à ce point et met à jour le seau (bucket) pour chaque zone automatique. Ensuite, la durée est ajustée par la nouvelle valeur de seau (bucket) et les données météo sont supprimées."
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Attention: mise à jour des données météo au moment du, ou après le, calcul"
            },
            header: "Mise à jour automatique des données météo",
            labels: {
              "auto-update-enabled": "Met à jour les données météo automatiquement",
              "auto-update-first-update": "(Première) Mise à jour à",
              "auto-update-interval": "Mettre à jour les données des capteurs toutes les",
              "auto-update-delay": "Délai de mise à jour",
              "auto-update-schedule": "Planning de mise à jour",
              "auto-update-time": "Mettre à jour à"
            },
            options: {
              days: "jours",
              hours: "heures",
              minutes: "minutes"
            },
            description: "Récupère et stocke les données météo automatiquement. Des données météo sont nécessaires pour calculer les seaux (buckets) par zone et les durées."
          },
          "automatic-clear": {
            header: "Délestage automatique des données météo",
            description: "Suppression automatique des données météo collectées à une heure données. Utilisez ceci pour être sûr qu'il n'y ait plus de restes des données météo des jours précédents. Ne supprimez pas les données météo avant le calcul et n'utilisez cette option que si vous vous attendez à ce que les données météo soient récupérées après le calcul du jour. Idéalement, vous voudrez \"élaguer\" les données les plus tard possible dans la journée.",
            labels: {
              "automatic-clear-enabled": "Suppression automatique des données météo collectées",
              "automatic-clear-time": "Supprimer les données météo à"
            }
          },
          continuousupdates: {
            header: "Mises à jour continues des capteurs (expérimental)",
            description: "Fonction expérimentale pour des données météo plus granulaires.",
            labels: {
              continuousupdates: "Activer les mises à jour continues",
              sensor_debounce: "Anti-rebond du capteur",
              "sensor-debounce": "Temps d'antirebond du capteur (ms)"
            }
          }
        },
        description: "Cette page fournit les réglages globaux.",
        title: "Général",
        sections: {
          weather: "Météo",
          automation: "Automatisation",
          location: "Emplacement",
          watering: "Comportement darrosage"
        }
      },
      help: {
        title: "Aide",
        cards: {
          "how-to-get-help": {
            title: "Comment obtenir de l'aide",
            "first-read-the": "Premièrement, lisez ",
            wiki: "Documentation",
            "if-you-still-need-help": "Si vous avez toujours besoin d'aide, adressez vous sur le",
            "community-forum": "forum communautaire",
            "or-open-a": "ou ouvrez un",
            "github-issue": "problème Github",
            "english-only": "en Anglais uniquement"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Ajouter un groupe de capteurs"
            },
            header: "Ajouter des groupes de capteurs"
          },
          mapping: {
            aggregates: {
              average: "Moyenne",
              first: "Premier",
              last: "Dernier",
              maximum: "Maximum",
              median: "Médian",
              minimum: "Minimum",
              sum: "Somme",
              riemannsum: "Somme de Riemann",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Vous ne pouvez pas supprimer ce groupe de capteurs car au moins une zone l'utilise.",
              invalid_source: "Source invalide",
              source_does_not_exist: "La source n'existe pas. Veuillez saisir une source valide, comme 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Point de rosée",
              evapotranspiration: "Évapotranspiration",
              humidity: "Humidité",
              "maximum temperature": "Température maximale",
              "minimum temperature": "Température minimale",
              precipitation: "Précipitation totale",
              pressure: "Pression",
              "solar radiation": "Rayonnement solaire",
              temperature: "Température",
              windspeed: "Vitesse du vent",
              "current precipitation": "Précipitations actuelles"
            },
            "sensor-aggregate-of-sensor-values-to-calculate": "des valeurs des capteurs pour calculer la durée",
            "sensor-aggregate-use-the": "Utiliser les",
            "sensor-entity": "Entité capteur",
            static_value: "Valeur",
            "input-units": "L'entité fournit des entrées en",
            source: "Source",
            sources: {
              none: "Aucun",
              weather_service: "Service météo",
              sensor: "Capteur",
              static: "Valeur statique"
            },
            pressure_types: {
              relative: "relative",
              absolute: "absolue"
            },
            "pressure-type": "La pression est",
            "sensor-units": "Le capteur fournit les valeurs en"
          }
        },
        description: "Ajouter un ou plusieurs groupes de capteurs qui récupèrent les données météo de Weather service, de capteurs locaux ou d'une combinaison de tous ceux-ci. Vous pouvez associer chaque groupe de capteurs avec une ou plusieurs zones",
        labels: {
          "mapping-name": "Nom"
        },
        no_items: "Il n'y a pas encore de groupe de capteurs définis.",
        title: "Groupes de capteurs",
        "weather-records": {
          title: "Relevés météo",
          timestamp: "Heure",
          temperature: "Temp.",
          humidity: "Humidity",
          precipitation: "Précip.",
          "retrieval-time": "Récupéré",
          "no-data": "Aucune donnée météo disponible pour ce groupe de capteurs",
          dewpoint: "Rosée",
          wind: "Vent",
          pressure: "Pression"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Ajouter un module"
            },
            header: "Ajout d'un module"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Vous ne pouvez pas supprimer ce module car au moins une zone l'utilise."
            },
            labels: {
              configuration: "Configuration",
              required: "indique un champ requis"
            },
            "translated-options": {
              DontEstimate: "Ne fait pas d'estimation",
              EstimateFromSunHours: "Estimation à partir des heures d'ensoleillement",
              EstimateFromTemp: "Estimation à partir de la température",
              EstimateFromSunHoursAndTemperature: "Estimer à partir de la moyenne des heures d'ensoleillement et de la température"
            }
          }
        },
        description: "Ajouter un ou plusieurs modules qui calcule la durée d'irrigation. Chaque module vient avec sa propre configuration et peut être utilisé pour calculer la durée d'irrigation d'une ou plusieurs zones.",
        no_items: "Il n'y a aucun module défini pour l'instant.",
        title: "Modules"
      },
      zones: {
        actions: {
          add: "Ajouter",
          calculate: "Calculer",
          information: "Informations",
          update: "Mise à jour",
          "reset-bucket": "Mise à zéro du seau (bucket)",
          "view-weather-info": "Voir données météo",
          "view-weather-info-message": "Données météo disponibles pour",
          "view-watering-calendar": "Calendrier d'arrosage",
          irrigate_all: "Arroser toutes les zones maintenant",
          open_settings: "Modifier les réglages"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Ajouter une zone"
            },
            header: "Ajout d'une zone"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Recalculer les durées",
              "update-all": "Actualiser les données météo",
              "reset-all-buckets": "Mise à zéro de tous les seaux (buckets)",
              "clear-all-weatherdata": "Mise à zéro de toutes les données météo"
            },
            header: "Actions sur toutes les zones"
          }
        },
        description: "Spécifiez une ou plusieurs zones d'irrigation ici. La durée d'irrigation est calculée par zone, en fonction de la taille, du débit, état, module et groupe de capteurs.",
        labels: {
          bucket: "Seau",
          duration: "Durée",
          "lead-time": "Délai",
          mapping: "Groupe de capteurs",
          "maximum-duration": "Durée maximale",
          multiplier: "Multiplicateur",
          name: "Nom",
          size: "Taille",
          state: "État",
          states: {
            automatic: "Automatique",
            disabled: "Désactivé",
            manual: "Manuel"
          },
          throughput: "Débit",
          "maximum-bucket": "Seau (bucket) maximum",
          last_calculated: "Dernier calcul",
          "data-last-updated": "Dernière mise à jour",
          "data-number-of-data-points": "Nombre de points de données",
          drainage_rate: "Taux de drainage",
          linked_entity: "Entité interrupteur/vanne liée",
          linked_entity_placeholder: "ex. switch.vanne_jardin",
          irrigate_now: "Irriguer maintenant",
          bucket_threshold: "Déficit minimum pour irriguer",
          flow_sensor: "Capteur de débitmètre (optionnel)",
          flow_sensor_placeholder: "p. ex. sensor.zone_flow_rate"
        },
        no_items: "Il n'y a pas encore de zone définie.",
        title: "Zones",
        confirm_irrigate: {
          title: "Démarrer l'arrosage ?",
          body: "Ceci ouvre maintenant la ou les vannes liées et ignore toutes les conditions d'exclusion (pluie, température, nombre minimal de jours entre les arrosages).",
          all_linked_zones: "Toutes les zones liées",
          toast_started: "Arrosage démarré",
          toast_failed: "Échec de l'arrosage"
        },
        status: {
          decision_disabled: "Désactivée — cette zone ne sera pas arrosée automatiquement.",
          decision_water: "Arrosage nécessaire : environ {duration} au prochain cycle programmé.",
          decision_water_at: "Arrosera environ {duration} à {time}.",
          decision_water_skip: "Déficit ~{duration}, mais le prochain cycle sera probablement ignoré ({reason}).",
          decision_water_no_schedule: "Déficit ~{duration} — aucun horaire n'arrose cette zone ; déclenchez-la manuellement.",
          decision_no_water: "Aucun arrosage nécessaire pour le moment — le sol a assez d'humidité.",
          decision_unknown: "Pas encore calculé — appuyez sur Mettre à jour, puis Calculer pour vérifier.",
          last_checked: "Dernière vérification",
          never: "jamais",
          saved: "Enregistré",
          estimate_now: "Maintenant",
          estimate_tag: "est.",
          estimate_method: {
            hourly: "Estimation en direct à partir de la météo horaire depuis le dernier calcul",
            proxy: "Estimation répartie à partir de la prévision du jour depuis le dernier calcul"
          }
        },
        help: {
          bucket: "Bilan d'humidité du sol (seau). Une valeur négative signifie que le sol est sec et que la zone a besoin d'eau.",
          calculate: "Calcule la durée d'arrosage à partir des dernières données. À lancer après Mettre à jour.",
          update: "Récupère les dernières données météo/capteurs pour cette zone.",
          irrigate_link_entity: "Associez un interrupteur/une vanne dans les réglages de cette zone pour activer l'arrosage manuel.",
          irrigate_all: "Ouvre maintenant les vannes liées de chaque zone en déficit. Les conditions d'exclusion (pluie, vent, température) sont ignorées.",
          update_all: "Collecte les dernières données météo/capteurs pour toutes les zones. Ne change pas les durées en soi.",
          calculate_all: "Recalcule la durée d'arrosage de chaque zone automatique à partir des données collectées jusqu'ici."
        },
        outlook: {
          next_run: "Prochain cycle",
          no_schedule: "Aucun horaire automatique — les zones ne s'arrosent que lorsque vous les déclenchez.",
          setup_schedule: "Configurer un horaire",
          targets_all: "toutes les zones",
          targets_zones: "{count} zones",
          will_skip: "Le prochain cycle sera probablement ignoré",
          will_run: "Les conditions semblent favorables pour le prochain cycle.",
          why_skipped: "Pourquoi ?",
          provisional: "prévision — peut changer",
          active_guards: "Conditions actives",
          last_run: "Dernier cycle",
          last_run_skipped: "ignoré",
          last_run_ran: "exécuté",
          today: "aujourd'hui",
          tomorrow: "demain",
          actions: {
            irrigate: "Arroser",
            calculate: "Recalculer",
            update: "Actualiser les données"
          },
          checks: {
            precipitation: "Pluie prévue",
            days_between: "Jours entre arrosages",
            temperature: "Température basse",
            wind: "Vent fort",
            rain_sensor: "Capteur de pluie"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} jours",
            temperature: "{observed}° (sous {threshold}°)",
            wind: "{observed} (au-dessus de {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Aucune donnée de calendrier d'arrosage disponible pour cette zone.",
          error_prefix: "Erreur lors de la génération du calendrier :",
          month: "Mois",
          et: "ET (mm)",
          precipitation: "Précipitations (mm)",
          watering: "Arrosage (L)",
          avg_temp: "Temp. moy. (°C)",
          method_prefix: "Méthode :"
        },
        confirm_action: {
          reset_bucket_title: "Réinitialiser le seau de cette zone ?",
          reset_bucket_body: "Cela remet le seau à 0 et supprime le bilan d'humidité accumulé pour cette zone.",
          reset_all_buckets_title: "Réinitialiser tous les seaux ?",
          reset_all_buckets_body: "Cela remet à 0 le seau de chaque zone et supprime le bilan d'humidité accumulé. Les calculs d'arrosage repartiront de zéro à la prochaine mise à jour.",
          clear_weather_title: "Effacer toutes les données météo ?",
          clear_weather_body: "Cela supprime tous les relevés météo et capteurs de toutes les zones. Les zones auront besoin de nouvelles données avant de pouvoir recalculer."
        }
      },
      schedules: {
        title: "Planifications",
        description: "Créez des planifications récurrentes pour calculer, mettre à jour ou irriguer automatiquement — sans automatisations.",
        add: "Ajouter une planification",
        no_items: "Aucune planification configurée. Cliquez sur 'Ajouter une planification'.",
        zones_all: "Toutes les zones",
        zones_specific: "Zones spécifiques",
        hours: "heures",
        minutes: "min",
        types: {
          daily: "Quotidien",
          weekly: "Hebdomadaire",
          monthly: "Mensuel",
          interval: "Toutes les N heures",
          sunrise: "Lever du soleil",
          sunset: "Coucher du soleil",
          solar_azimuth: "Azimut solaire"
        },
        actions: {
          calculate: "Calculer (mettre à jour la durée d'irrigation)",
          update: "Mettre à jour (collecter données météo)",
          irrigate: "Irriguer (contrôler les vannes directement)"
        },
        days: {
          monday: "Lu",
          tuesday: "Ma",
          wednesday: "Me",
          thursday: "Je",
          friday: "Ve",
          saturday: "Sa",
          sunday: "Di"
        },
        fields: {
          name: "Nom",
          type: "Type de planification",
          enabled: "Activé",
          time: "Heure (HH:MM)",
          days_of_week: "Jours de la semaine",
          day_of_month: "Jour du mois",
          interval_hours: "Intervalle",
          action: "Action",
          zones: "Zones",
          start_date: "Date de début (optionnel)",
          end_date: "Date de fin (optionnel)",
          offset_minutes: "Décalage par rapport au lever/coucher du soleil",
          account_for_duration: "Démarrer tôt pour que l'irrigation se termine à l'heure cible",
          azimuth_angle: "Angle d'azimut solaire",
          time_anchor: "Lheure correspond au"
        },
        dialog: {
          add_title: "Ajouter une planification",
          edit_title: "Modifier la planification"
        },
        time_anchor: {
          start: "Début de larrosage",
          finish: "Fin de larrosage"
        }
      },
      info: {
        title: "Infos",
        description: "Afficher les informations sur la prochaine irrigation et l'état du système.",
        "configuration-not-available": "Configuration non disponible.",
        cards: {
          "zone-bucket-values": {
            title: "Valeurs de réservoir et durée",
            labels: {
              bucket: "Réservoir",
              duration: "Durée"
            },
            "no-zones": "Aucune zone configurée"
          },
          "next-irrigation": {
            title: "Prochaine irrigation",
            labels: {
              "next-start": "Prochain démarrage",
              duration: "Durée",
              zones: "Zones"
            },
            "no-data": "Aucune donnée disponible"
          },
          "irrigation-reason": {
            title: "Raison d'irrigation",
            labels: {
              reason: "Raison",
              sunrise: "Lever du soleil",
              "total-duration": "Durée totale",
              explanation: "Explication"
            },
            "no-data": "Aucune donnée disponible"
          },
          irrigate_now: {
            title: "Irriguer maintenant",
            description: "Démarrer immédiatement l'irrigation pour toutes les zones avec une entité liée. Les conditions d'exclusion sont ignorées.",
            button_all: "Démarrer toutes les zones maintenant",
            no_linked_zones: "Aucune zone n'a d'entité interrupteur/vanne liée avec une durée calculée."
          }
        }
      },
      setup: {
        title: "Configuration"
      }
    },
    Pt = "Smart Irrigation",
    Mt = {
      title: "Coordonnées de Localisation",
      description: "Configurez les coordonnées de localisation pour la récupération des données météo. Vous pouvez utiliser des coordonnées manuelles différentes de votre emplacement Home Assistant si nécessaire.",
      manual_enabled: "Utiliser des coordonnées manuelles",
      use_ha_location: "Utiliser l'emplacement Home Assistant",
      latitude: "Latitude (degrés décimaux)",
      longitude: "Longitude (degrés décimaux)",
      elevation: "Élévation (mètres au-dessus du niveau de la mer)",
      current_ha_coords: "Coordonnées actuelles de Home Assistant"
    },
    Dt = {
      title: "Jours entre irrigations",
      description: "Configurez le nombre minimum de jours entre les événements d'irrigation.",
      label: "Jours minimum entre irrigations",
      help_text: "Définissez 0 pour désactiver. Les valeurs de 1 à 365 jours sont supportées."
    },
    Ct = {
      title: "Déclencheurs de démarrage d'arrosage",
      description: "Configurez le moment où l'arrosage doit démarrer en fonction des événements solaires. Vous pouvez ajouter plusieurs déclencheurs pour différents horaires. Pour les déclencheurs au lever du soleil, laisser le décalage à 0 utilisera automatiquement la durée totale de toutes les zones activées.",
      add_trigger: "Ajouter un déclencheur",
      edit_trigger: "Modifier le déclencheur",
      delete_trigger: "Supprimer le déclencheur",
      trigger_types: {
        sunrise: "Lever du soleil",
        sunset: "Coucher du soleil",
        solar_azimuth: "Azimut solaire"
      },
      fields: {
        name: {
          name: "Nom du déclencheur",
          description: "Un nom descriptif pour identifier ce déclencheur"
        },
        type: {
          name: "Type de déclencheur",
          description: "Le type d'événement solaire qui déclenche"
        },
        enabled: {
          name: "Activé",
          description: "Si ce déclencheur est actuellement actif"
        },
        offset_minutes: {
          name: "Décalage (minutes)",
          description: "Minutes avant (-) ou après (+) l'événement solaire. Pour les déclencheurs au lever du soleil, utilisez 0 pour une temporisation automatique basée sur la durée totale des zones."
        },
        azimuth_angle: {
          name: "Angle d'azimut (degrés)",
          description: "Angle d'azimut solaire en degrés où 0=Nord, 90=Est, 180=Sud, 270=Ouest"
        },
        account_for_duration: {
          name: "Tenir compte de la durée",
          description: "Si activé, l'arrosage démarrera suffisamment tôt pour se terminer à l'heure indiquée. Si désactivé, l'arrosage démarrera exactement à l'heure indiquée."
        }
      },
      dialog: {
        add_title: "Ajouter un déclencheur de démarrage d'arrosage",
        edit_title: "Modifier le déclencheur de démarrage d'arrosage",
        cancel: "Annuler",
        save: "Enregistrer",
        delete: "Supprimer"
      },
      no_triggers: "Aucun déclencheur de démarrage d'arrosage configuré. Le système utilisera le comportement par défaut (lever du soleil avec la durée totale des zones). Ajoutez des déclencheurs pour personnaliser le démarrage de l'arrosage.",
      offset_auto: "Automatique (calculé à partir de la durée totale des zones)",
      confirm_delete: "Voulez-vous vraiment supprimer le déclencheur '{name}' ?",
      validation: {
        name_required: "Le nom du déclencheur est requis",
        azimuth_invalid: "L'angle d'azimut doit être un nombre valide"
      },
      help: {
        sunrise_offset: "Pour les déclencheurs au lever du soleil : utilisez des valeurs négatives pour démarrer avant le lever, positives pour démarrer après. Mettez 0 pour démarrer automatiquement assez tôt pour terminer toutes les zones avant le lever du soleil.",
        sunset_offset: "Pour les déclencheurs au coucher du soleil : utilisez des valeurs négatives pour démarrer avant le coucher, positives pour démarrer après.",
        azimuth_explanation: "L'azimut solaire est la direction de la boussole du soleil. 0°=Nord, 90°=Est, 180°=Sud, 270°=Ouest. Vous pouvez saisir n'importe quelle valeur d'angle (p. ex. 450° = 90°, -30° = 330°). Utilisez ceci pour déclencher l'arrosage lorsque le soleil atteint une position précise.",
        multiple_triggers: "Vous pouvez configurer plusieurs déclencheurs. Chaque déclencheur activé planifiera les démarrages d'arrosage de manière indépendante."
      }
    },
    Ht = {
      title: "Conditions d'exclusion",
      description: "Ignorer automatiquement l'irrigation quand les conditions sont défavorables. Les vérifications de précipitations, température et vent nécessitent un service météo.",
      threshold_label: "Seuil de précipitations",
      threshold_description: "Précipitations totales minimales prévues (en mm) sur la fenêtre de prévision pour ignorer l'irrigation.",
      lookahead_label: "Fenêtre de prévision (jours)",
      lookahead_help: "Nombre de jours de prévision à venir additionnés lors de la vérification de la pluie. La prévision commence demain (aujourd'hui est exclu), donc 1 = uniquement le lendemain, 2 = les deux prochains jours, etc.",
      temp_section_title: "Ignorer par basse température",
      temp_threshold_label: "Ignorer si température en dessous de",
      wind_section_title: "Ignorer par vent fort",
      wind_threshold_label: "Ignorer si vitesse du vent supérieure à",
      rain_sensor_section_title: "Condition du capteur de pluie",
      rain_sensor_label: "Entité capteur de pluie (optionnel)",
      rain_sensor_placeholder: "ex. binary_sensor.pluie"
    },
    Lt = {
      title: "Séquençage des zones",
      description: "Lorsque plusieurs zones ont besoin d'irrigation, choisissez si elles fonctionnent simultanément ou l'une après l'autre. En mode séquentiel, le système attend que chaque zone se termine avant de démarrer la suivante.",
      parallel: "Parallèle (toutes les zones simultanément)",
      sequential: "Séquentiel (une zone à la fois)",
      rotating: "Rotatif (les zones se relaient)",
      max_consecutive_duration_label: "Durée d'exécution consécutive max. par zone",
      max_consecutive_duration_unit: "minutes",
      min_absorption_time_label: "Temps d'absorption min. entre les passages",
      min_absorption_time_unit: "minutes (0 = désactivé)"
    },
    Bt = {
      title: "Service météo",
      description: "Configurez le service météo à utiliser pour les calculs d'ET et les conditions de saut.",
      enabled_label: "Activer le service météo",
      service_label: "Service météo",
      api_key_label: "Clé API",
      api_key_placeholder: "Laisser vide pour conserver la clé existante",
      api_key_configured: "La clé API est configurée",
      api_key_not_configured: "Aucune clé API configurée",
      api_key_help: "Une clé API de votre fournisseur de service météo choisi. Open-Meteo ne nécessite pas de clé. OpenWeatherMap et Pirate Weather offrent tous deux des offres gratuites.",
      no_api_key_needed: "Open-Meteo est un service gratuit et ne nécessite aucune clé API.",
      save_button: "Enregistrer les paramètres météo",
      saved: "Paramètres météo enregistrés",
      openmeteo: "Open-Meteo (gratuit, sans clé)",
      test_button: "Tester la connexion",
      test_button_testing: "Test en cours…",
      test_success: "✓ Connexion réussie",
      test_error_invalid_auth: "✗ Clé API invalide — vérifiez qu'elle est correcte et active",
      test_error_cannot_connect: "✗ Connexion impossible — vérifiez votre connexion internet",
      test_error_no_service: "✗ Sélectionnez d'abord un service météo",
      test_error_unknown: "✗ Échec du test — erreur inconnue",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    Nt = {
      zone_size: "La surface arrosée totale de cette zone. Utilisée avec le débit pour calculer la quantité d'eau appliquée par passage.",
      zone_throughput: "Débit d'eau total de votre système d'arrosage pour cette zone (litres/min en métrique, gal/min en impérial). Consultez la fiche technique de vos arroseurs ou mesurez le temps nécessaire pour remplir un récipient de volume connu.",
      zone_drainage_rate: "La vitesse à laquelle l'eau excédentaire s'évacue du sol lorsque le réservoir est plein. Typique : pelouse 50 mm/h, sol sableux 100+ mm/h, argile 10 mm/h.",
      zone_bucket: "Déficit (négatif) ou excédent (positif) d'eau actuel de cette zone. L'arrosage se déclenche lorsque le réservoir descend sous le seuil.",
      zone_maximum_bucket: "Excédent d'humidité maximal que la zone peut retenir. L'eau au-delà de ce niveau est considérée comme du ruissellement. Valeur typique : 50 mm.",
      zone_bucket_threshold: "L'arrosage se déclenche lorsque le réservoir descend sous cette valeur. Doit être 0 ou négatif. 0 signifie arroser dès qu'il y a un déficit.",
      zone_multiplier: "Facteur d'échelle appliqué à la durée calculée. Au-dessus de 1,0 pour augmenter, en dessous de 1,0 pour diminuer. Utile pour un réglage fin sans modifier les mesures physiques.",
      zone_lead_time: "Secondes supplémentaires avant le démarrage de l'arrosage. À utiliser pour la mise en chauffe de la pompe ou la mise en pression du système.",
      zone_maximum_duration: "Plafond strict pour un seul passage d'arrosage en secondes. Empêche un arrosage incontrôlé. Par défaut : 3600 s (1 heure).",
      zone_linked_entity: "L'entité interrupteur ou vanne de HA qui contrôle le débit d'eau de cette zone. Cette entité est activée lorsque l'arrosage fonctionne.",
      zone_flow_sensor: "Capteur optionnel mesurant le débit d'eau réel. Utilisé uniquement pour le rapport — n'affecte pas les calculs de durée.",
      general_autoupdatedelay: "Secondes à attendre après le démarrage de HA avant la première récupération des données météo. Permet aux autres intégrations de s'initialiser d'abord.",
      general_sensor_debounce: "Écart minimal en millisecondes entre les lectures du capteur pour filtrer le bruit des capteurs qui changent rapidement.",
      general_calctime: "Heure de la journée à laquelle les durées d'arrosage sont recalculées à partir des données météo collectées. Format : HH:MM (24 heures).",
      general_cleardatatime: "Heure de la journée à laquelle les anciennes données météo sont purgées. Doit être réglée après l'heure de calcul.",
      general_days_between: "Nombre minimal de jours entre les arrosages d'une même zone. Mettre 0 pour désactiver (arroser dès qu'il y a un déficit).",
      general_autoupdateinterval: "Fréquence de collecte des données météo. Choisissez une valeur qui équilibre la fraîcheur des données et les limites de l'API.",
      general_precipitation_threshold: "L'arrosage est ignoré si le total des précipitations prévues sur la fenêtre de prévision dépasse cette valeur.",
      general_temp_threshold: "L'arrosage est ignoré si la température actuelle est inférieure à cette valeur (p. ex. pour éviter les dégâts du gel).",
      general_wind_threshold: "L'arrosage est ignoré si la vitesse du vent dépasse cette valeur (un vent fort réduit l'efficacité et provoque une dérive)."
    },
    It = {
      title: "Assistant de configuration",
      open_button: "Assistant de configuration",
      close: "Fermer",
      next: "Suivant",
      back: "Retour",
      finish: "Terminer",
      skip_step: "Ignorer cette étape",
      step_indicator: "Étape {current} sur {total}",
      setup_complete_banner: "Configuration non terminée. Lancez l'assistant pour commencer.",
      open_wizard: "Ouvrir l'assistant",
      steps: {
        welcome: {
          title: "Bienvenue dans Smart Irrigation",
          intro: "Cet assistant vous guide à travers les quatre étapes nécessaires pour que votre première zone arrose automatiquement.",
          step1_label: "Service météo — où obtenir les données météo",
          step2_label: "Module de calcul — comment la durée d'arrosage est calculée",
          step3_label: "Groupe de capteurs — quelles sources de données utiliser",
          step4_label: "Zone — votre première zone d'arrosage",
          tip: "Vous pouvez ignorer n'importe quelle étape et la configurer plus tard depuis l'onglet Configuration."
        },
        weather: {
          title: "Service météo",
          description: "Choisissez comment obtenir les données météo. Open-Meteo est gratuit et ne nécessite pas de clé API — c'est le choix le plus simple pour la plupart des utilisateurs."
        },
        module: {
          title: "Module de calcul",
          description: "Un module calcule la durée d'arrosage en fonction de l'évapotranspiration (ET). Le module PyETO (méthode FAO-56) est recommandé pour la plupart des utilisateurs.",
          pick_label: "Sélectionner le type de module",
          no_modules: "Aucun type de module disponible."
        },
        mapping: {
          title: "Groupe de capteurs",
          description: "Un groupe de capteurs relie chaque variable météo à une source de données. Définissez les variables clés ci-dessous — vous pourrez affiner chaque association de capteur plus tard depuis l'onglet Configuration → Groupes de capteurs.",
          name_label: "Nom du groupe de capteurs",
          source_label: "Source de données pour",
          use_weather_service: "Service météo",
          use_sensor: "Capteur",
          use_static: "Valeur statique",
          use_none: "Aucune / non utilisé"
        },
        zone: {
          title: "Première zone",
          description: "Une zone est une surface d'arrosage (p. ex. pelouse, massif). Définissez les propriétés physiques pour que le système puisse calculer la durée d'arrosage correcte.",
          name_label: "Nom de la zone",
          size_label: "Surface",
          throughput_label: "Débit de l'arroseur",
          entity_label: "Interrupteur ou vanne lié",
          entity_placeholder: "p. ex. switch.garden_valve",
          module_label: "Module de calcul",
          mapping_label: "Groupe de capteurs"
        },
        done: {
          title: "Configuration terminée !",
          description: "Votre première zone est prête. Smart Irrigation calculera désormais les durées d'arrosage automatiquement à partir des données météo.",
          next_steps: "Ce que vous pouvez faire ensuite :",
          tip1: "Allez dans Zones pour voir les durées calculées et les valeurs du réservoir.",
          tip2: "Ajoutez d'autres zones depuis l'onglet Zones.",
          tip3: "Affinez tous les paramètres depuis l'onglet Configuration.",
          go_zones: "Aller aux Zones",
          go_setup: "Aller à la Configuration"
        }
      },
      stepper: {
        weather: "Météo",
        module: "Module",
        mapping: "Groupe de capteurs",
        zone: "Zone"
      },
      confirm_close: {
        body: "Fermer lassistant de configuration ? Votre progression est enregistrée.",
        keep: "Continuer",
        close: "Fermer"
      }
    },
    Ot = {
      common: St,
      defaults: Et,
      module: xt,
      calcmodules: Tt,
      panels: jt,
      title: Pt,
      coordinate_config: Mt,
      days_between_irrigation: Dt,
      irrigation_start_triggers: Ct,
      weather_skip: Ht,
      zone_sequencing: Lt,
      weather_service_config: Bt,
      field_help: Nt,
      wizard: It
    },
    $t = Object.freeze({
      __proto__: null,
      common: St,
      defaults: Et,
      module: xt,
      calcmodules: Tt,
      panels: jt,
      title: Pt,
      coordinate_config: Mt,
      days_between_irrigation: Dt,
      irrigation_start_triggers: Ct,
      weather_skip: Ht,
      zone_sequencing: Lt,
      weather_service_config: Bt,
      field_help: Nt,
      wizard: It,
      default: Ot
    }),
    Rt = {
      actions: {
        delete: "Cancella",
        edit: "Modifica",
        save: "Salva",
        cancel: "Annulla",
        confirm_delete: "Conferma eliminazione",
        confirm_delete_zone: "Vuoi davvero eliminare questa zona?"
      },
      labels: {
        module: "Modulo",
        no: "No",
        select: "Seleziona",
        yes: "Si",
        enabled: "Abilitato",
        disabled: "Disabilitato",
        before: "prima",
        after: "dopo",
        settings: "Impostazioni",
        bulk_actions: "Azioni multiple"
      },
      units: {
        seconds: "secondi"
      },
      attributes: {
        size: "dimensione",
        throughput: "portata",
        state: "stato",
        bucket: "serbatoio",
        last_updated: "ultimo aggiornamento",
        last_calculated: "ultimo calcolo",
        number_of_data_points: "numero di punti dati"
      },
      loading: "Caricamento",
      saving: "Salvataggio",
      "loading-messages": {
        configuration: "Caricamento configurazione...",
        modules: "Caricamento moduli...",
        general: "Caricamento..."
      },
      "saving-messages": {
        adding: "Aggiungendo...",
        saving: "Salvataggio..."
      },
      errors: {
        load_failed: "Impossibile caricare i dati",
        save_failed: "Impossibile salvare le modifiche",
        delete_failed: "Impossibile eliminare",
        action_failed: "Azione non riuscita"
      }
    },
    Vt = {
      "default-zone": "Zona predefinita",
      "default-mapping": "Mappatura predefinita"
    },
    Ut = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Il modulo ha restituito un deficit di evapotraspirazione del",
          "bucket-was": "Il secchio era",
          "new-bucket-values-is": "Il nuovo valore del secchio è",
          bucket: "secchio",
          "old-bucket-variable": "old_bucket",
          "max-bucket-variable": "max_bucket",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Poiché secchio < 0, è necessaria l'irrigazione",
          "steps-taken-to-calculate-duration": "Per calcolare la durata esatta, sono stati eseguiti i seguenti passaggi",
          "precipitation-rate-defined-as": "Il tasso di precipitazione è definito come",
          "duration-is-calculated-as": "La durata viene calcolata come",
          drainage: "drenaggio",
          "drainage-rate": "tasso_di_drenaggio",
          hours: "ore",
          "precipitation-rate-variable": "tasso_di_precipitazione",
          "multiplier-is-applied": "Ora viene applicato il moltiplicatore. Il moltiplicatore è",
          "duration-after-multiplier-is": "quindi la durata è",
          "maximum-duration-is-applied": "Quindi, viene applicata la durata massima. La durata massima è",
          "duration-after-maximum-duration-is": "quindi la durata è",
          "lead-time-is-applied": "Infine, viene applicato il lead time. Il tempo di consegna è",
          "duration-after-lead-time-is": "quindi la durata finale è",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Poiché secchio >= 0, non è necessaria alcuna irrigazione e la durata è impostata su",
          "maximum-bucket-is": "la dimensione massima del secchio è",
          "drainage-rate-is": "Il tasso di drenaggio a saturazione (serbatoio al massimo) è",
          "current-drainage-is": "Il drenaggio attuale è calcolato come",
          "no-drainage": "Il drenaggio attuale è 0 perché"
        }
      }
    },
    qt = {
      pyeto: {
        description: "Calcola la durata in base al calcolo FAO56 dalla libreria PyETO"
      },
      static: {
        description: "Modulo 'fittizio' con un delta configurabile statico"
      },
      passthrough: {
        description: "Modulo passthrough che restituisce il valore di un sensore di Evapotraspirazione sotto forma di delta"
      }
    },
    Zt = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Calcolo automatico della durata",
            description: "Il calcolo prende i dati meteorologici raccolti fino a quel momento e aggiorna il bucket per ciascuna zona automatica. Quindi, la durata viene regolata in base al nuovo valore del segmento e i dati meteorologici raccolti vengono rimossi.",
            labels: {
              "auto-calc-enabled": "Calcola automaticamente la durata delle zone",
              "auto-calc-time": "Calcola a",
              "calc-time": "Calcola alle"
            }
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Attenzione: ora di aggiornamento dei dati meteorologici in corrispondenza o dopo l'ora di calcolo"
            },
            header: "Aggiornamento automatico dei dati meteorologici",
            description: "Raccogli e archivia automaticamente i dati meteorologici. I dati meteorologici sono necessari per calcolare gli intervalli e le durate delle zone.",
            labels: {
              "auto-update-enabled": "Aggiorna automaticamente i dati meteorologici",
              "auto-update-first-update": "(Primo) aggiornamento alle",
              "auto-update-interval": "Aggiorna i dati del sensore ogni",
              "auto-update-schedule": "Pianificazione aggiornamento",
              "auto-update-time": "Aggiorna alle",
              "auto-update-delay": "Ritardo di aggiornamento"
            },
            options: {
              days: "giorni",
              hours: "ore",
              minutes: "minuti"
            }
          },
          "automatic-clear": {
            header: "Eliminazione automatica dei dati meteo",
            description: "Rimuovi automaticamente i dati meteo raccolti a un orario configurato. Usa questa opzione per assicurarti che non vi siano dati meteo residui dei giorni precedenti. Non rimuovere i dati meteo prima di effettuare il calcolo e utilizza questa opzione solo se prevedi che l'aggiornamento automatico raccolga i dati meteo dopo aver effettuato il calcolo giornaliero. Idealmente, la rimozione dei dati meteo dovrebbe avvenire il più tardi possibile.",
            labels: {
              "automatic-clear-enabled": "Cancella automaticamente i dati meteorologici raccolti",
              "automatic-clear-time": "Cancella dati meteo a"
            }
          },
          continuousupdates: {
            header: "Aggiornamenti continui sensori (sperimentale)",
            description: "Funzione sperimentale per dati meteo più granulari.",
            labels: {
              continuousupdates: "Abilita gli aggiornamenti continui",
              sensor_debounce: "Rimbalzo del sensore",
              "sensor-debounce": "Tempo anti-rimbalzo sensore (ms)"
            }
          }
        },
        description: "Questa pagina fornisce le impostazioni globali.",
        title: "Generale",
        sections: {
          weather: "Meteo",
          automation: "Automazione",
          location: "Posizione",
          watering: "Comportamento di irrigazione"
        }
      },
      help: {
        title: "Aiuto",
        cards: {
          "how-to-get-help": {
            title: "Come ottenere aiuto",
            "first-read-the": "Per prima cosa, leggi il",
            wiki: "Documentazione",
            "if-you-still-need-help": "Se hai ancora bisogno di aiuto, contatta il",
            "community-forum": "Forum della Comunità",
            "or-open-a": "oppure apri un",
            "github-issue": "Problema su Github",
            "english-only": "soltanto in Inglese"
          }
        }
      },
      info: {
        title: "Info",
        description: "Visualizza informazioni sulla prossima irrigazione e lo stato del sistema.",
        cards: {
          "next-irrigation": {
            title: "Prossima irrigazione",
            labels: {
              "next-start": "Prossimo avvio",
              duration: "Durata",
              zones: "Zone"
            },
            "no-data": "Nessun dato disponibile",
            "backend-todo": "TODO: API di backend necessaria per le informazioni sull'irrigazione"
          },
          "irrigation-reason": {
            title: "Motivo irrigazione",
            labels: {
              reason: "Ragione",
              sunrise: "Alba",
              "total-duration": "Durata totale",
              explanation: "Spiegazione"
            },
            "no-data": "Nessun dato disponibile",
            "backend-todo": "TODO: API di backend necessaria per le informazioni sull'irrigazione"
          },
          "zone-bucket-values": {
            title: "Valori serbatoio e durata",
            labels: {
              bucket: "Serbatoio",
              duration: "Durata"
            },
            "no-zones": "Nessuna zona configurata"
          },
          irrigate_now: {
            title: "Irriga ora",
            description: "Avvia immediatamente l'irrigazione per tutte le zone con entità collegata. Le condizioni di esclusione vengono ignorate.",
            button_all: "Avvia tutte le zone ora",
            no_linked_zones: "Nessuna zona ha un'entità interruttore/valvola collegata con durata calcolata."
          }
        },
        "configuration-not-available": "Configurazione non disponibile."
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Aggiungi gruppo di sensori"
            },
            header: "Aggiungi gruppo di sensori"
          },
          mapping: {
            aggregates: {
              average: "Media",
              first: "Primo",
              last: "Ultimo",
              maximum: "Massimo",
              median: "Mediana",
              minimum: "Minimo",
              riemannsum: "Somma di Riemann",
              sum: "Somma",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Non è possibile eliminare questo gruppo di sensori perché almeno una zona lo utilizza.",
              invalid_source: "Fonte non valida",
              source_does_not_exist: "La fonte non esiste. Inserire una fonte valida, ad esempio 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Punto di rugiada",
              evapotranspiration: "Evapotraspirazione",
              humidity: "Umidità",
              "maximum temperature": "Temperatura massima",
              "minimum temperature": "Temperatura minima",
              precipitation: "Precipitazione",
              "current precipitation": "Precipitazioni attuali",
              pressure: "Pressione",
              "solar radiation": "Irradiamento solare",
              temperature: "Temperatura",
              windspeed: "Velocità del vento"
            },
            pressure_types: {
              absolute: "assoluta",
              relative: "relativa"
            },
            "pressure-type": "La pressione è",
            "sensor-aggregate-of-sensor-values-to-calculate": "dei valori del sensore per calcolare la durata",
            "sensor-aggregate-use-the": "Usa il",
            "sensor-entity": "Entità sensore",
            static_value: "Valore",
            "input-units": "L'input fornisce valori in",
            source: "Fonte",
            sources: {
              none: "Nessuna",
              weather_service: "Servizio meteo",
              sensor: "Sensore",
              static: "Valore statico"
            }
          }
        },
        description: "Aggiungi uno o più gruppi di sensori che recuperano i dati meteorologici da Weather service, da sensori o da una combinazione di questi. È possibile mappare ciascun gruppo di sensori su una o più zone",
        labels: {
          "mapping-name": "Nome"
        },
        no_items: "Non è ancora stato definito alcun gruppo di sensori.",
        title: "Gruppi di sensori",
        "weather-records": {
          title: "Record meteo (ultimi 10)",
          timestamp: "Tempo",
          temperature: "Temp.",
          humidity: "Umidità",
          precipitation: "Precip.",
          "retrieval-time": "Recuperato",
          "no-data": "Non sono disponibili dati meteo per questo gruppo di sensori",
          dewpoint: "Rugiada",
          wind: "Vento",
          pressure: "Press."
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Aggiungi modulo"
            },
            header: "Aggiungi modulo"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Non puoi eliminare questo modulo perché almeno una zona lo utilizza."
            },
            labels: {
              configuration: "Configurazione",
              required: "indica un campo richiesto"
            },
            "translated-options": {
              DontEstimate: "Non stimare",
              EstimateFromSunHours: "Stima dalle ore solari",
              EstimateFromTemp: "Stima dalla temperatura",
              EstimateFromSunHoursAndTemperature: "Stima dalla media delle ore di sole e della temperatura"
            }
          }
        },
        description: "Aggiungi uno o più moduli che calcolano la durata dell'irrigazione. Ogni modulo viene fornito con la propria configurazione e può essere utilizzato per calcolare la durata di una o più zone.",
        no_items: "Non ci sono ancora moduli definiti.",
        title: "Moduli"
      },
      zones: {
        actions: {
          add: "Aggiungi",
          calculate: "Calcola",
          information: "Informazioni",
          update: "Aggiorna",
          "reset-bucket": "Reimposta il secchio",
          "view-weather-info": "Visualizza dati meteo",
          "view-weather-info-message": "Informazioni meteo disponibili per",
          "view-weather-info-todo": "TODO: Implementare la navigazione ai dettagli del gruppo di sensori",
          "view-watering-calendar": "Calendario irrigazione",
          irrigate_all: "Irriga tutte le zone ora",
          open_settings: "Modifica impostazioni"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Aggiungi zona"
            },
            header: "Aggiungi zona"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Ricalcola le durate",
              "update-all": "Aggiorna i dati meteo",
              "reset-all-buckets": "Reimposta tutte le zone",
              "clear-all-weatherdata": "Cancella tutti i dati meteo"
            },
            header: "Azioni su tutte le zone"
          }
        },
        description: "Specificare qui una o più zone di irrigazione. La durata dell'irrigazione viene calcolata per zona, a seconda delle dimensioni, della produttività, dello stato, del modulo e del gruppo di sensori.",
        labels: {
          bucket: "Secchio",
          duration: "Durata",
          "lead-time": "Tempi di esecuzione",
          mapping: "Gruppo di sensori",
          "maximum-duration": "Durata massima",
          multiplier: "Moltiplicatore",
          name: "Nome",
          size: "Misura",
          state: "Stato",
          states: {
            automatic: "Automatico",
            disabled: "Disabilitato",
            manual: "Manuale"
          },
          throughput: "Portata",
          "maximum-bucket": "Secchio massimo",
          last_calculated: "Ultimo calcolo",
          "data-last-updated": "Ultimo aggiornamento dei dati",
          "data-number-of-data-points": "Numero di dati",
          tasso_di_drenaggio: "tasso di drenaggio",
          drainage_rate: "Tasso di drenaggio",
          linked_entity: "Entità interruttore/valvola collegata",
          linked_entity_placeholder: "es. switch.valvola_giardino",
          irrigate_now: "Irriga ora",
          bucket_threshold: "Deficit minimo per irrigare",
          flow_sensor: "Sensore del flussometro (opzionale)",
          flow_sensor_placeholder: "ad es. sensor.zone_flow_rate"
        },
        no_items: "Non ci sono ancora zone definite.",
        title: "Zone",
        confirm_irrigate: {
          title: "Avviare l'irrigazione?",
          body: "Verranno aperte ora le valvole collegate, ignorando tutte le condizioni di esclusione (pioggia, temperatura, giorni minimi tra le irrigazioni).",
          all_linked_zones: "Tutte le zone collegate",
          toast_started: "Irrigazione avviata",
          toast_failed: "Irrigazione non riuscita"
        },
        status: {
          decision_disabled: "Disattivata — questa zona non verrà irrigata automaticamente.",
          decision_water: "Irrigazione necessaria: circa {duration} alla prossima esecuzione programmata.",
          decision_water_at: "Irrigherà circa {duration} alle {time}.",
          decision_water_skip: "Deficit ~{duration}, ma la prossima esecuzione sarà probabilmente saltata ({reason}).",
          decision_water_no_schedule: "Deficit ~{duration} — nessuna pianificazione irriga questa zona; avviala manualmente.",
          decision_no_water: "Nessuna irrigazione necessaria ora — il terreno ha umidità sufficiente.",
          decision_unknown: "Non ancora calcolato — premi Aggiorna, poi Calcola per verificare.",
          last_checked: "Ultimo controllo",
          never: "mai",
          saved: "Salvato",
          estimate_now: "Ora",
          estimate_tag: "stima",
          estimate_method: {
            hourly: "Stima live dai dati meteo orari dall'ultimo calcolo",
            proxy: "Stima distribuita dalla previsione di oggi dall'ultimo calcolo"
          }
        },
        help: {
          bucket: "Bilancio di umidità del suolo (secchio). Un valore negativo significa che il terreno è asciutto e la zona ha bisogno d'acqua.",
          calculate: "Calcola la durata dell'irrigazione dai dati più recenti. Eseguilo dopo Aggiorna.",
          update: "Recupera i dati meteo/sensori più recenti per questa zona.",
          irrigate_link_entity: "Collega un interruttore/una valvola nelle impostazioni di questa zona per abilitare l'irrigazione manuale.",
          irrigate_all: "Apre subito le valvole collegate per ogni zona in deficit. Le condizioni di esclusione (pioggia, vento, temperatura) vengono ignorate.",
          update_all: "Raccoglie i dati meteo/sensori più recenti per tutte le zone. Non modifica da sola le durate.",
          calculate_all: "Ricalcola la durata di irrigazione di ogni zona automatica dai dati raccolti finora."
        },
        outlook: {
          next_run: "Prossima esecuzione",
          no_schedule: "Nessuna pianificazione automatica — le zone si irrigano solo quando le avvii tu.",
          setup_schedule: "Configura una pianificazione",
          targets_all: "tutte le zone",
          targets_zones: "{count} zone",
          will_skip: "La prossima esecuzione sarà probabilmente saltata",
          will_run: "Le condizioni sembrano favorevoli per la prossima esecuzione.",
          why_skipped: "Perché?",
          provisional: "previsione — può cambiare",
          active_guards: "Condizioni attive",
          last_run: "Ultima esecuzione",
          last_run_skipped: "saltata",
          last_run_ran: "eseguita",
          today: "oggi",
          tomorrow: "domani",
          actions: {
            irrigate: "Irriga",
            calculate: "Ricalcola",
            update: "Aggiorna dati"
          },
          checks: {
            precipitation: "Pioggia prevista",
            days_between: "Giorni tra le irrigazioni",
            temperature: "Temperatura bassa",
            wind: "Vento forte",
            rain_sensor: "Sensore di pioggia"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} giorni",
            temperature: "{observed}° (sotto {threshold}°)",
            wind: "{observed} (sopra {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Nessun dato del calendario di irrigazione disponibile per questa zona.",
          error_prefix: "Errore nella generazione del calendario:",
          month: "Mese",
          et: "ET (mm)",
          precipitation: "Precipitazioni (mm)",
          watering: "Irrigazione (L)",
          avg_temp: "Temp. media (°C)",
          method_prefix: "Metodo:"
        },
        confirm_action: {
          reset_bucket_title: "Azzerare il secchio di questa zona?",
          reset_bucket_body: "Questo riporta il secchio a 0, scartando il bilancio di umidità accumulato per questa zona.",
          reset_all_buckets_title: "Azzerare tutti i secchi?",
          reset_all_buckets_body: "Questo riporta a 0 il secchio di ogni zona, scartando il bilancio di umidità accumulato. I calcoli di irrigazione ripartiranno dal prossimo aggiornamento.",
          clear_weather_title: "Cancellare tutti i dati meteo?",
          clear_weather_body: "Questo elimina tutti i record meteo e dei sensori di tutte le zone. Le zone avranno bisogno di nuovi dati prima di poter ricalcolare."
        }
      },
      schedules: {
        title: "Pianificazioni",
        description: "Crea pianificazioni ricorrenti per calcolare, aggiornare o irrigare automaticamente — senza automazioni.",
        add: "Aggiungi pianificazione",
        no_items: "Nessuna pianificazione configurata. Fare clic su 'Aggiungi pianificazione'.",
        zones_all: "Tutte le zone",
        zones_specific: "Zone specifiche",
        hours: "ore",
        minutes: "min",
        types: {
          daily: "Giornaliero",
          weekly: "Settimanale",
          monthly: "Mensile",
          interval: "Ogni N ore",
          sunrise: "Alba",
          sunset: "Tramonto",
          solar_azimuth: "Azimut solare"
        },
        actions: {
          calculate: "Calcola (aggiorna durata irrigazione)",
          update: "Aggiorna (raccogliere dati meteo)",
          irrigate: "Irriga (controllare valvole direttamente)"
        },
        days: {
          monday: "Lu",
          tuesday: "Ma",
          wednesday: "Me",
          thursday: "Gi",
          friday: "Ve",
          saturday: "Sa",
          sunday: "Do"
        },
        fields: {
          name: "Nome",
          type: "Tipo di pianificazione",
          enabled: "Abilitato",
          time: "Ora (HH:MM)",
          days_of_week: "Giorni della settimana",
          day_of_month: "Giorno del mese",
          interval_hours: "Intervallo",
          action: "Azione",
          zones: "Zone",
          start_date: "Data di inizio (opzionale)",
          end_date: "Data di fine (opzionale)",
          offset_minutes: "Offset dall'alba/tramonto",
          account_for_duration: "Iniziare prima affinché l'irrigazione finisca all'orario target",
          azimuth_angle: "Angolo di azimut solare",
          time_anchor: "Lorario indica"
        },
        dialog: {
          add_title: "Aggiungi pianificazione",
          edit_title: "Modifica pianificazione"
        },
        time_anchor: {
          start: "Inizio dellirrigazione",
          finish: "Fine dellirrigazione"
        }
      },
      setup: {
        title: "Configurazione"
      }
    },
    Ft = "Smart Irrigation",
    Wt = {
      title: "Coordinate di Posizione",
      description: "Configura le coordinate di posizione per il recupero dei dati meteorologici. Puoi usare coordinate manuali diverse dalla tua posizione Home Assistant se necessario.",
      manual_enabled: "Usa coordinate manuali",
      use_ha_location: "Usa posizione di Home Assistant",
      latitude: "Latitudine (gradi decimali)",
      longitude: "Longitudine (gradi decimali)",
      elevation: "Elevazione (metri sul livello del mare)",
      current_ha_coords: "Coordinate attuali di Home Assistant"
    },
    Gt = {
      title: "Giorni tra irrigazioni",
      description: "Configura il numero minimo di giorni tra gli eventi di irrigazione.",
      label: "Giorni minimi tra irrigazioni",
      help_text: "Impostare 0 per disabilitare. Sono supportati valori da 1 a 365 giorni."
    },
    Kt = {
      title: "Trigger di avvio irrigazione",
      description: "Configura quando deve iniziare l'irrigazione in base agli eventi solari. Puoi aggiungere più trigger per orari diversi. Per i trigger all'alba, lasciando lo scostamento a 0 verrà usata automaticamente la durata totale di tutte le zone abilitate.",
      add_trigger: "Aggiungi trigger",
      edit_trigger: "Modifica trigger",
      delete_trigger: "Elimina trigger",
      trigger_types: {
        sunrise: "Alba",
        sunset: "Tramonto",
        solar_azimuth: "Azimut solare"
      },
      fields: {
        name: {
          name: "Nome del trigger",
          description: "Un nome descrittivo per identificare questo trigger"
        },
        type: {
          name: "Tipo di trigger",
          description: "Il tipo di evento solare su cui attivare"
        },
        enabled: {
          name: "Abilitato",
          description: "Se questo trigger è attualmente attivo"
        },
        offset_minutes: {
          name: "Scostamento (minuti)",
          description: "Minuti prima (-) o dopo (+) l'evento solare. Per i trigger all'alba, usa 0 per una temporizzazione automatica basata sulla durata totale delle zone."
        },
        azimuth_angle: {
          name: "Angolo di azimut (gradi)",
          description: "Angolo di azimut solare in gradi dove 0=Nord, 90=Est, 180=Sud, 270=Ovest"
        },
        account_for_duration: {
          name: "Considera la durata",
          description: "Se abilitato, l'irrigazione inizierà abbastanza presto da terminare all'ora specificata. Se disabilitato, l'irrigazione inizierà esattamente all'ora specificata."
        }
      },
      dialog: {
        add_title: "Aggiungi trigger di avvio irrigazione",
        edit_title: "Modifica trigger di avvio irrigazione",
        cancel: "Annulla",
        save: "Salva",
        delete: "Elimina"
      },
      no_triggers: "Nessun trigger di avvio irrigazione configurato. Il sistema userà il comportamento predefinito (alba con la durata totale delle zone). Aggiungi trigger per personalizzare l'avvio dell'irrigazione.",
      offset_auto: "Automatico (calcolato dalla durata totale delle zone)",
      confirm_delete: "Vuoi davvero eliminare il trigger '{name}'?",
      validation: {
        name_required: "Il nome del trigger è obbligatorio",
        azimuth_invalid: "L'angolo di azimut deve essere un numero valido"
      },
      help: {
        sunrise_offset: "Per i trigger all'alba: usa valori negativi per iniziare prima dell'alba, positivi per iniziare dopo. Imposta 0 per iniziare automaticamente con abbastanza anticipo da completare tutte le zone prima dell'alba.",
        sunset_offset: "Per i trigger al tramonto: usa valori negativi per iniziare prima del tramonto, positivi per iniziare dopo il tramonto.",
        azimuth_explanation: "L'azimut solare è la direzione bussolare del sole. 0°=Nord, 90°=Est, 180°=Sud, 270°=Ovest. Puoi inserire qualsiasi valore di angolo (ad es. 450° = 90°, -30° = 330°). Usalo per attivare l'irrigazione quando il sole raggiunge una posizione specifica.",
        multiple_triggers: "Puoi configurare più trigger. Ogni trigger abilitato pianificherà gli avvii dell'irrigazione in modo indipendente."
      }
    },
    Xt = {
      title: "Condizioni di esclusione",
      description: "Salta automaticamente l'irrigazione quando le condizioni sono sfavorevoli. I controlli di precipitazioni, temperatura e vento richiedono un servizio meteo.",
      threshold_label: "Soglia di precipitazioni",
      threshold_description: "Precipitazione totale minima prevista (in mm) sulla finestra di previsione per saltare l'irrigazione.",
      lookahead_label: "Finestra di previsione (giorni)",
      lookahead_help: "Quanti giorni di previsione futuri sommare nel controllo della pioggia. La previsione parte da domani (oggi è escluso), quindi 1 = solo il giorno successivo, 2 = i prossimi due giorni, e così via.",
      temp_section_title: "Salta per bassa temperatura",
      temp_threshold_label: "Salta se temperatura sotto",
      wind_section_title: "Salta per vento forte",
      wind_threshold_label: "Salta se velocità del vento superiore a",
      rain_sensor_section_title: "Condizione sensore pioggia",
      rain_sensor_label: "Entità sensore pioggia (opzionale)",
      rain_sensor_placeholder: "es. binary_sensor.pioggia"
    },
    Yt = {
      title: "Sequenza zone",
      description: "Quando più zone necessitano di irrigazione, scegliere se funzionano contemporaneamente o una dopo l'altra. In modalità sequenziale, il sistema attende che ogni zona finisca prima di avviare la successiva. In modalità rotante, il sistema alterna tra le zone assegnando a ciascuna un tempo massimo consecutivo prima di passare alla successiva.",
      parallel: "Parallelo (tutte le zone insieme)",
      sequential: "Sequenziale (una zona alla volta)",
      rotating: "Rotante (le zone si alternano)",
      max_consecutive_duration_label: "Tempo massimo consecutivo per zona",
      max_consecutive_duration_unit: "minuti",
      min_absorption_time_label: "Tempo minimo di assorbimento tra slot",
      min_absorption_time_unit: "minuti (0 = disabilitato)"
    },
    Jt = {
      title: "Servizio meteo",
      description: "Configura quale servizio meteo usare per i calcoli ET e le condizioni di salto.",
      enabled_label: "Abilita servizio meteo",
      service_label: "Servizio meteo",
      api_key_label: "Chiave API",
      api_key_placeholder: "Lascia vuoto per mantenere la chiave esistente",
      api_key_configured: "La chiave API è configurata",
      api_key_not_configured: "Nessuna chiave API configurata",
      api_key_help: "Una chiave API del provider di servizio meteo scelto. Open-Meteo non richiede una chiave. OpenWeatherMap e Pirate Weather offrono entrambi piani gratuiti.",
      no_api_key_needed: "Open-Meteo è un servizio gratuito e non richiede una chiave API.",
      save_button: "Salva impostazioni meteo",
      saved: "Impostazioni meteo salvate",
      openmeteo: "Open-Meteo (gratuito, senza chiave)",
      test_button: "Prova connessione",
      test_button_testing: "Test in corso…",
      test_success: "✓ Connessione riuscita",
      test_error_invalid_auth: "✗ Chiave API non valida — verifica che sia corretta e attiva",
      test_error_cannot_connect: "✗ Impossibile connettersi — controlla la connessione internet",
      test_error_no_service: "✗ Seleziona prima un servizio meteo",
      test_error_unknown: "✗ Test fallito — errore sconosciuto",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    Qt = {
      zone_size: "L'area irrigata totale di questa zona. Usata con la portata per calcolare quanta acqua viene erogata per ciclo.",
      zone_throughput: "Flusso d'acqua totale del tuo impianto di irrigazione per questa zona (litri/min in metrico, gal/min in imperiale). Controlla la scheda tecnica degli irrigatori o misura cronometrando quanto tempo serve a riempire un contenitore di volume noto.",
      zone_drainage_rate: "La velocità con cui l'acqua in eccesso drena dal terreno quando il secchio è pieno. Tipico: prato 50 mm/h, terreno sabbioso 100+ mm/h, argilla 10 mm/h.",
      zone_bucket: "Deficit (negativo) o surplus (positivo) idrico attuale di questa zona. L'irrigazione si attiva quando il secchio scende sotto la soglia.",
      zone_maximum_bucket: "Surplus di umidità massimo che la zona può trattenere. L'acqua oltre questo livello è trattata come deflusso. Valore tipico: 50 mm.",
      zone_bucket_threshold: "L'irrigazione si attiva quando il secchio scende sotto questo valore. Deve essere 0 o negativo. 0 significa irrigare ogni volta che c'è un deficit.",
      zone_multiplier: "Fattore di scala applicato alla durata calcolata. Sopra 1,0 aumenta, sotto 1,0 diminuisce. Utile per la messa a punto senza modificare le misure fisiche.",
      zone_lead_time: "Secondi aggiuntivi prima dell'avvio dell'irrigazione. Usali per il riscaldamento della pompa o la pressurizzazione dell'impianto.",
      zone_maximum_duration: "Limite massimo assoluto per un singolo ciclo di irrigazione in secondi. Previene irrigazioni incontrollate. Predefinito: 3600 s (1 ora).",
      zone_linked_entity: "L'entità interruttore o valvola di HA che controlla il flusso d'acqua per questa zona. Questa entità viene attivata quando l'irrigazione è in funzione.",
      zone_flow_sensor: "Sensore opzionale che misura la portata d'acqua effettiva. Usato solo per i report — non influisce sul calcolo della durata.",
      general_autoupdatedelay: "Secondi di attesa dopo l'avvio di HA prima del primo recupero dei dati meteo. Consente alle altre integrazioni di inizializzarsi prima.",
      general_sensor_debounce: "Intervallo minimo in millisecondi tra le letture del sensore per filtrare il rumore dei sensori che cambiano rapidamente.",
      general_calctime: "Ora del giorno in cui le durate di irrigazione vengono ricalcolate dai dati meteo raccolti. Formato: HH:MM (24 ore).",
      general_cleardatatime: "Ora del giorno in cui i vecchi dati meteo vengono eliminati. Deve essere impostata dopo l'ora di calcolo.",
      general_days_between: "Giorni minimi tra gli eventi di irrigazione per la stessa zona. Imposta 0 per disabilitare (irrigare ogni volta che c'è un deficit).",
      general_autoupdateinterval: "Con quale frequenza vengono raccolti i dati meteo. Scegli un valore che bilanci dati aggiornati e limiti dell'API.",
      general_precipitation_threshold: "L'irrigazione viene saltata se le precipitazioni totali previste sulla finestra di previsione superano questa quantità.",
      general_temp_threshold: "L'irrigazione viene saltata se la temperatura attuale è inferiore a questo valore (ad es. per prevenire danni da gelo).",
      general_wind_threshold: "L'irrigazione viene saltata se la velocità del vento supera questo valore (il vento forte riduce l'efficienza e causa deriva)."
    },
    ea = {
      title: "Configurazione guidata",
      open_button: "Configurazione guidata",
      close: "Chiudi",
      next: "Avanti",
      back: "Indietro",
      finish: "Fine",
      skip_step: "Salta questo passaggio",
      step_indicator: "Passaggio {current} di {total}",
      setup_complete_banner: "Configurazione non completata. Avvia la procedura guidata per iniziare.",
      open_wizard: "Apri procedura guidata",
      steps: {
        welcome: {
          title: "Benvenuto in Smart Irrigation",
          intro: "Questa procedura guidata ti accompagna nei quattro passaggi necessari per far irrigare automaticamente la tua prima zona.",
          step1_label: "Servizio meteo — dove ottenere i dati meteo",
          step2_label: "Modulo di calcolo — come viene calcolata la durata dell'irrigazione",
          step3_label: "Gruppo di sensori — quali fonti di dati usare",
          step4_label: "Zona — la tua prima zona di irrigazione",
          tip: "Puoi saltare qualsiasi passaggio e configurarlo in seguito dalla scheda Configurazione."
        },
        weather: {
          title: "Servizio meteo",
          description: "Scegli come ottenere i dati meteo. Open-Meteo è gratuito e non richiede una chiave API — è la scelta più semplice per la maggior parte degli utenti."
        },
        module: {
          title: "Modulo di calcolo",
          description: "Un modulo calcola quanto irrigare in base all'evapotraspirazione (ET). Il modulo PyETO (metodo FAO-56) è consigliato per la maggior parte degli utenti.",
          pick_label: "Seleziona il tipo di modulo",
          no_modules: "Nessun tipo di modulo disponibile."
        },
        mapping: {
          title: "Gruppo di sensori",
          description: "Un gruppo di sensori collega ogni variabile meteo a una fonte di dati. Imposta le variabili chiave qui sotto — potrai perfezionare le singole associazioni dei sensori in seguito dalla scheda Configurazione → Gruppi di sensori.",
          name_label: "Nome del gruppo di sensori",
          source_label: "Fonte di dati per",
          use_weather_service: "Servizio meteo",
          use_sensor: "Sensore",
          use_static: "Valore statico",
          use_none: "Nessuna / non usata"
        },
        zone: {
          title: "Prima zona",
          description: "Una zona è un'area di irrigazione (ad es. prato, aiuola). Imposta le proprietà fisiche affinché il sistema possa calcolare la durata di irrigazione corretta.",
          name_label: "Nome della zona",
          size_label: "Area",
          throughput_label: "Portata dell'irrigatore",
          entity_label: "Interruttore o valvola collegati",
          entity_placeholder: "ad es. switch.garden_valve",
          module_label: "Modulo di calcolo",
          mapping_label: "Gruppo di sensori"
        },
        done: {
          title: "Configurazione completata!",
          description: "La tua prima zona è pronta. Smart Irrigation calcolerà ora le durate di irrigazione automaticamente in base ai dati meteo.",
          next_steps: "Cosa puoi fare ora:",
          tip1: "Vai su Zone per vedere le durate calcolate e i valori del secchio.",
          tip2: "Aggiungi altre zone dalla scheda Zone.",
          tip3: "Perfeziona tutte le impostazioni dalla scheda Configurazione.",
          go_zones: "Vai a Zone",
          go_setup: "Vai a Configurazione"
        }
      },
      stepper: {
        weather: "Meteo",
        module: "Modulo",
        mapping: "Gruppo di sensori",
        zone: "Zona"
      },
      confirm_close: {
        body: "Chiudere la procedura guidata? I progressi finora sono salvati.",
        keep: "Continua",
        close: "Chiudi"
      }
    },
    ta = {
      common: Rt,
      defaults: Vt,
      module: Ut,
      calcmodules: qt,
      panels: Zt,
      title: Ft,
      coordinate_config: Wt,
      days_between_irrigation: Gt,
      irrigation_start_triggers: Kt,
      weather_skip: Xt,
      zone_sequencing: Yt,
      weather_service_config: Jt,
      field_help: Qt,
      wizard: ea
    },
    aa = Object.freeze({
      __proto__: null,
      common: Rt,
      defaults: Vt,
      module: Ut,
      calcmodules: qt,
      panels: Zt,
      title: Ft,
      coordinate_config: Wt,
      days_between_irrigation: Gt,
      irrigation_start_triggers: Kt,
      weather_skip: Xt,
      zone_sequencing: Yt,
      weather_service_config: Jt,
      field_help: Qt,
      wizard: ea,
      default: ta
    }),
    ia = {
      actions: {
        delete: "Verwijderen",
        edit: "Bewerken",
        save: "Opslaan",
        cancel: "Annuleren",
        confirm_delete: "Verwijderen bevestigen",
        confirm_delete_zone: "Weet je zeker dat je deze zone wilt verwijderen?"
      },
      labels: {
        module: "Module",
        no: "Nee",
        select: "Kies",
        yes: "Ja",
        enabled: "Ingeschakeld",
        disabled: "Uitgeschakeld",
        before: "voor",
        after: "na",
        settings: "Instellingen",
        bulk_actions: "Bulkacties"
      },
      attributes: {
        size: "afmeting",
        throughput: "doorvoer",
        state: "status",
        bucket: "emmer",
        last_updated: "laatste update",
        last_calculated: "laatste berekening",
        number_of_data_points: "aantal datapunten"
      },
      loading: "Laden",
      saving: "Opslaan",
      units: {
        seconds: "seconden"
      },
      "loading-messages": {
        configuration: "Configuratie laden...",
        modules: "Modules laden...",
        general: "Laden..."
      },
      "saving-messages": {
        adding: "Toevoegen...",
        saving: "Opslaan..."
      },
      errors: {
        load_failed: "Kan gegevens niet laden",
        save_failed: "Kan wijzigingen niet opslaan",
        delete_failed: "Kan niet verwijderen",
        action_failed: "Actie mislukt"
      }
    },
    na = {
      "default-zone": "Standaard zone",
      "default-mapping": "Standaard sensorgroep"
    },
    ra = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "NB: in deze uitleg wordt de '.' as decimaalscheidingsteken gebruikt, worden afgeronde en metrische getallen getoond. Module berekende ET waarde van",
          "bucket-was": "Voorraad was",
          "new-bucket-values-is": "Nieuwe voorraad is",
          "old-bucket-variable": "oude_voorraad",
          delta: "verandering",
          "bucket-less-than-zero-irrigation-necessary": "Omdat de voorraad < 0 is, is irrigatie nodig",
          "steps-taken-to-calculate-duration": "On de exacte duur te berekenen werd het volgende gedaan",
          "precipitation-rate-defined-as": "De neerslag is",
          "duration-is-calculated-as": "De duur is",
          bucket: "voorraad",
          "precipitation-rate-variable": "neerslag",
          "multiplier-is-applied": "De vermenigvuldiger wordt toegepast. Deze is",
          "duration-after-multiplier-is": "dus de duur is",
          "maximum-duration-is-applied": "De maximum duur wordt toegepast. Deze is",
          "duration-after-maximum-duration-is": "dus de duur is",
          "lead-time-is-applied": "As laatste wordt de aanlooptijd toegepast. Deze is",
          "duration-after-lead-time-is": "dus de uiteindelijke duur is",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Omdat de voorraad >= 0 is er geen irrigatie nodig en is de duur gelijk aan",
          "maximum-bucket-is": "maximale voorraad grootte is",
          "max-bucket-variable": "max_bucket",
          drainage: "afwatering",
          "drainage-rate": "afwateringssnelheid",
          hours: "uren",
          "drainage-rate-is": "Drainagesnelheid bij verzadiging (emmer op maximum) is",
          "current-drainage-is": "Huidige drainage berekend als",
          "no-drainage": "Huidige drainage is 0 omdat"
        }
      }
    },
    oa = {
      pyeto: {
        description: "Bereken duur op basis van de FAU56 formule en de PyETO library"
      },
      static: {
        description: "Module met instelbare verandering"
      },
      passthrough: {
        description: "Geeft waarde van ET sensor as verandering terug"
      }
    },
    sa = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Automatische berekening van irrigatietijd",
            description: "Bij het berekenen wordt de verzamelde weersinformatie gebruikt om the voorraad en irrigatieduur per zone aan te passen. Daarna wordt de verzamelde weersinformatie verwijderd.",
            labels: {
              "auto-calc-enabled": "Automatisch irrigatietijd berekening voor elke zone",
              "auto-calc-time": "Berekenen op",
              "calc-time": "Berekenen om"
            }
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Let op: het automatisch bijwerken van weersinformatie vind plaats op of na de automatische berekening van irrigatietijd"
            },
            header: "Automatisch bijwerken van weersinformatie",
            description: "Verzamel en bewaar weersinformatie automatisch. Weersinformatie is nodig om vorraad en irrigatieduur per zone te berekenen.",
            labels: {
              "auto-update-enabled": "Automatisch weersinformatie bijwerken",
              "auto-update-delay": "Vertraging",
              "auto-update-interval": "Sensor data bijwerken elke",
              "auto-update-schedule": "Updateschema",
              "auto-update-time": "Bijwerken om"
            },
            options: {
              days: "dagen",
              hours: "uren",
              minutes: "minuten"
            }
          },
          "automatic-clear": {
            header: "Automatisch weersinformatie opruimen",
            description: "Verwijder weersinformatie op het ingestelde moment. Dit zorgt ervoor dat er geen weersinformatie van de vorige dag gebruikt kan worden voor berekeningen. Let op: verwijder geen weersinformatie voordat de berekening heeft plaatsgevonden. Gebruik deze optie als je verwacht dat er weersinformatie zal worden verzameld nadat de berekeningen voor de dag gedaan zijn. Verwijder weersinformatie zo laat mogelijk op de dag.",
            labels: {
              "automatic-clear-enabled": "Automatisch weersinformatie verwijderen",
              "automatic-clear-time": "Verwijder weersinformatie om"
            }
          },
          continuousupdates: {
            header: "Continue sensorupdates (experimenteel)",
            description: "Experimentele functie voor gedetailleerdere weergegevens.",
            labels: {
              continuousupdates: "Continue updates inschakelen",
              sensor_debounce: "Sensor-debounce",
              "sensor-debounce": "Sensor-debouncetijd (ms)"
            }
          }
        },
        description: "Dit zijn de algemene instellingen.",
        title: "Algemeen",
        sections: {
          weather: "Weer",
          automation: "Automatisering",
          location: "Locatie",
          watering: "Bewateringsgedrag"
        }
      },
      help: {
        title: "Hulp",
        cards: {
          "how-to-get-help": {
            title: "Hulp vragen",
            "first-read-the": "Allereerst, lees de",
            wiki: "Documentatie",
            "if-you-still-need-help": "Als je hierna nog steeds hulp nodig hebt, laat een bericht achter op het",
            "community-forum": "Communityforum",
            "or-open-a": "of open een",
            "github-issue": "GitHub-issue",
            "english-only": "alleen Engels"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Toevoegen"
            },
            header: "Voeg sensorgroep toe"
          },
          mapping: {
            aggregates: {
              average: "Gemiddelde",
              first: "Eerste",
              last: "Laatste",
              maximum: "Maximum",
              median: "Mediaan",
              minimum: "Minimum",
              sum: "Totaal",
              riemannsum: "Riemann-som",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Deze sensorgroep kan niet worden verwijderd omdat er minimaal een zone gebruik van maakt.",
              invalid_source: "Ongeldige bron",
              source_does_not_exist: "Bron bestaat niet. Voer een geldige bron in, zoals 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Dauwpunt",
              evapotranspiration: "Verdamping",
              humidity: "Vochtigheid",
              "maximum temperature": "Maximum temperatuur",
              "minimum temperature": "Minimum temperatuur",
              precipitation: "Totale neerslag",
              pressure: "Druk",
              "solar radiation": "Zonnestraling",
              temperature: "Temperatuur",
              windspeed: "Wind snelheid",
              "current precipitation": "Huidige neerslag"
            },
            pressure_types: {
              absolute: "absoluut",
              relative: "relatief"
            },
            "pressure-type": "Druk is",
            "sensor-aggregate-of-sensor-values-to-calculate": "van de sensor waardes om irrigatietijd te berekenen",
            "sensor-aggregate-use-the": "Gebruik de/het",
            "sensor-entity": "Sensor entiteit",
            "input-units": "Invoer geeft waardes in",
            static_value: "Waarde",
            source: "Bron",
            sources: {
              none: "Geen",
              weather_service: "Weerdienst",
              sensor: "Sensor",
              static: "Vaste waarde"
            }
          }
        },
        description: "Voeg een of meer sensorgroepen toe die weergegevens ophalen van Weather service, van sensoren of een combinatie. Elke sensorgroep kan worden gebruikt voor een of meerdere zones",
        labels: {
          "mapping-name": "Naam"
        },
        no_items: "Er zijn nog geen sensorgroepen.",
        title: "Sensorgroepen",
        "weather-records": {
          title: "Weerregistraties",
          timestamp: "Tijd",
          temperature: "Temp.",
          humidity: "Humidity",
          precipitation: "Neersl.",
          "retrieval-time": "Opgehaald",
          "no-data": "Geen weergegevens beschikbaar voor deze sensorgroep",
          dewpoint: "Dauw",
          wind: "Wind",
          pressure: "Druk"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Toevoegen"
            },
            header: "Voeg module toe"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Deze module kan niet worden verwijderd omdat er minimaal een zone gebruik van maakt."
            },
            labels: {
              configuration: "Instellingen",
              required: "verplicht veld"
            },
            "translated-options": {
              DontEstimate: "Niet berekenen",
              EstimateFromSunHours: "Gebaseerd op zon uren",
              EstimateFromTemp: "Gebaseerd op temperatuur",
              EstimateFromSunHoursAndTemperature: "Schatten op basis van het gemiddelde van zonuren en temperatuur"
            }
          }
        },
        description: "Voeg een of meerdere modules toe. Modules berekenen irrigatietijd. Elke module heeft zijn eigen configuratie and kan worden gebruikt voor het berekening van irrigatietijd voor een of meerdere zones.",
        no_items: "Er zijn nog geen modules.",
        title: "Modules"
      },
      zones: {
        actions: {
          add: "Toevoegen",
          calculate: "Bereken",
          information: "Informatie",
          update: "Bijwerken",
          "reset-bucket": "Leeg voorraad",
          "view-weather-info": "Weergegevens bekijken",
          "view-weather-info-message": "Weergegevens beschikbaar voor",
          "view-watering-calendar": "Bewateringskalender",
          irrigate_all: "Alle zones nu bewateren",
          open_settings: "Instellingen bewerken"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Toevoegen"
            },
            header: "Voeg zone toe"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Duur herberekenen",
              "update-all": "Weergegevens vernieuwen",
              "reset-all-buckets": "Leeg alle voorraden",
              "clear-all-weatherdata": "Verwijder alle weersinformatie"
            },
            header: "Acties voor alle zones"
          }
        },
        description: "Voeg een of meerdere zones toe. Per zone wordt de irrigatietijd berekend, afhankelijk van de afmeting, doorvoer, status, module en sensorgroep.",
        labels: {
          bucket: "Voorraad",
          duration: "Irrigatieduur",
          "lead-time": "Aanlooptijd",
          mapping: "Sensorgroep",
          "maximum-duration": "Maximale duur",
          multiplier: "Vermenigvuldiger",
          name: "Naam",
          size: "Afmeting",
          state: "Status",
          states: {
            automatic: "Automatisch",
            disabled: "Uit",
            manual: "Manueel"
          },
          throughput: "Doorvoer",
          "maximum-bucket": "Maximale voorraad",
          last_calculated: "Berekend op",
          "data-last-updated": "Bijgewerkt op",
          "data-number-of-data-points": "Aantal datapunten",
          drainage_rate: "Afwateringssnelheid",
          linked_entity: "Gekoppelde schakelaar/klep-entiteit",
          linked_entity_placeholder: "bijv. switch.tuin_klep",
          irrigate_now: "Nu bewateren",
          bucket_threshold: "Minimum tekort voor bewatering",
          flow_sensor: "Doorstroommeter-sensor (optioneel)",
          flow_sensor_placeholder: "bijv. sensor.zone_flow_rate"
        },
        no_items: "Er zijn nog geen zones.",
        title: "Zones",
        confirm_irrigate: {
          title: "Irrigatie starten?",
          body: "Dit opent nu de gekoppelde klep(pen) en negeert alle uitsluitingsvoorwaarden (regen, temperatuur, minimaal aantal dagen tussen beurten).",
          all_linked_zones: "Alle gekoppelde zones",
          toast_started: "Irrigatie gestart",
          toast_failed: "Irrigatie mislukt"
        },
        status: {
          decision_disabled: "Uitgeschakeld — deze zone wordt niet automatisch bewaterd.",
          decision_water: "Bewatering nodig: ongeveer {duration} bij de volgende geplande beurt.",
          decision_water_at: "Bewatert ongeveer {duration} om {time}.",
          decision_water_skip: "Tekort ~{duration}, maar de volgende beurt wordt waarschijnlijk overgeslagen ({reason}).",
          decision_water_no_schedule: "Tekort ~{duration} — geen schema bewatert deze zone; start handmatig.",
          decision_no_water: "Nu geen bewatering nodig — de bodem heeft genoeg vocht.",
          decision_unknown: "Nog niet berekend — druk op Bijwerken en daarna Bereken om te controleren.",
          last_checked: "Laatst gecontroleerd",
          never: "nooit",
          saved: "Opgeslagen",
          estimate_now: "Nu",
          estimate_tag: "schat.",
          estimate_method: {
            hourly: "Live schatting op basis van uurlijks weer sinds de laatste berekening",
            proxy: "Schatting verdeeld op basis van de verwachting van vandaag sinds de laatste berekening"
          }
        },
        help: {
          bucket: "Bodemvochtbalans (voorraad). Een negatieve waarde betekent dat de bodem droog is en de zone water nodig heeft.",
          calculate: "Berekent op basis van de nieuwste gegevens hoe lang er bewaterd wordt. Voer dit uit na Bijwerken.",
          update: "Haalt de nieuwste weer-/sensorgegevens voor deze zone op.",
          irrigate_link_entity: "Koppel een schakelaar/klep in de instellingen van deze zone om handmatig bewateren mogelijk te maken.",
          irrigate_all: "Opent nu de gekoppelde kleppen voor elke zone met een tekort. Uitsluitingsvoorwaarden (regen, wind, temperatuur) worden genegeerd.",
          update_all: "Verzamelt de nieuwste weer-/sensorgegevens voor alle zones. Verandert op zichzelf de duur niet.",
          calculate_all: "Herberekent de bewateringsduur van elke automatische zone op basis van de tot nu toe verzamelde gegevens."
        },
        outlook: {
          next_run: "Volgende beurt",
          no_schedule: "Geen automatisch schema — zones worden alleen bewaterd wanneer je ze handmatig start.",
          setup_schedule: "Een schema instellen",
          targets_all: "alle zones",
          targets_zones: "{count} zones",
          will_skip: "Volgende beurt wordt waarschijnlijk overgeslagen",
          will_run: "De omstandigheden lijken gunstig voor de volgende beurt.",
          why_skipped: "Waarom?",
          provisional: "voorspelling — kan veranderen",
          active_guards: "Actieve voorwaarden",
          last_run: "Laatste beurt",
          last_run_skipped: "overgeslagen",
          last_run_ran: "uitgevoerd",
          today: "vandaag",
          tomorrow: "morgen",
          actions: {
            irrigate: "Bewateren",
            calculate: "Herberekenen",
            update: "Gegevens vernieuwen"
          },
          checks: {
            precipitation: "Regenverwachting",
            days_between: "Dagen tussen beurten",
            temperature: "Lage temperatuur",
            wind: "Harde wind",
            rain_sensor: "Regensensor"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} dagen",
            temperature: "{observed}° (onder {threshold}°)",
            wind: "{observed} (boven {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Geen bewateringskalendergegevens beschikbaar voor deze zone.",
          error_prefix: "Fout bij het genereren van de kalender:",
          month: "Maand",
          et: "ET (mm)",
          precipitation: "Neerslag (mm)",
          watering: "Bewatering (L)",
          avg_temp: "Gem. temp. (°C)",
          method_prefix: "Methode:"
        },
        confirm_action: {
          reset_bucket_title: "Voorraad van deze zone resetten?",
          reset_bucket_body: "Dit zet de voorraad terug op 0 en verwijdert de opgebouwde vochtbalans voor deze zone.",
          reset_all_buckets_title: "Alle voorraden resetten?",
          reset_all_buckets_body: "Dit zet de voorraad van elke zone terug op 0 en verwijdert de opgebouwde vochtbalans. De bewateringsberekening begint opnieuw bij de volgende update.",
          clear_weather_title: "Alle weergegevens wissen?",
          clear_weather_body: "Dit verwijdert alle verzamelde weer- en sensorgegevens van alle zones. De zones hebben nieuwe gegevens nodig voordat ze opnieuw kunnen berekenen."
        }
      },
      schedules: {
        title: "Schema's",
        description: "Maak terugkerende schema's voor automatisch berekenen, bijwerken of bewateren — zonder automatiseringen.",
        add: "Schema toevoegen",
        no_items: "Nog geen schema's geconfigureerd. Klik op 'Schema toevoegen'.",
        zones_all: "Alle zones",
        zones_specific: "Specifieke zones",
        hours: "uur",
        minutes: "min",
        types: {
          daily: "Dagelijks",
          weekly: "Wekelijks",
          monthly: "Maandelijks",
          interval: "Elke N uur",
          sunrise: "Zonsopgang",
          sunset: "Zonsondergang",
          solar_azimuth: "Zonneazimut"
        },
        actions: {
          calculate: "Berekenen (bewateringsduur bijwerken)",
          update: "Bijwerken (weergegevens verzamelen)",
          irrigate: "Bewateren (kleppen direct aansturen)"
        },
        days: {
          monday: "Ma",
          tuesday: "Di",
          wednesday: "Wo",
          thursday: "Do",
          friday: "Vr",
          saturday: "Za",
          sunday: "Zo"
        },
        fields: {
          name: "Naam",
          type: "Schematype",
          enabled: "Ingeschakeld",
          time: "Tijd (HH:MM)",
          days_of_week: "Weekdagen",
          day_of_month: "Dag van de maand",
          interval_hours: "Interval",
          action: "Actie",
          zones: "Zones",
          start_date: "Startdatum (optioneel)",
          end_date: "Einddatum (optioneel)",
          offset_minutes: "Offset van zonsopgang/-ondergang",
          account_for_duration: "Vroeg starten zodat bewatering eindigt op doeltijd",
          azimuth_angle: "Zonneazimuthoek",
          time_anchor: "Tijd markeert het"
        },
        dialog: {
          add_title: "Schema toevoegen",
          edit_title: "Schema bewerken"
        },
        time_anchor: {
          start: "Begin van de bewatering",
          finish: "Einde van de bewatering"
        }
      },
      info: {
        title: "Info",
        description: "Informatie bekijken over de volgende bewatering en systeemstatus.",
        "configuration-not-available": "Configuratie niet beschikbaar.",
        cards: {
          "zone-bucket-values": {
            title: "Zone-emmerwaarden & duur",
            labels: {
              bucket: "Emmer",
              duration: "Duur"
            },
            "no-zones": "Geen zones geconfigureerd"
          },
          "next-irrigation": {
            title: "Volgende bewatering",
            labels: {
              "next-start": "Volgende start",
              duration: "Duur",
              zones: "Zones"
            },
            "no-data": "Geen gegevens beschikbaar"
          },
          "irrigation-reason": {
            title: "Reden voor bewatering",
            labels: {
              reason: "Reden",
              sunrise: "Zonsopgang",
              "total-duration": "Totale duur",
              explanation: "Uitleg"
            },
            "no-data": "Geen gegevens beschikbaar"
          },
          irrigate_now: {
            title: "Nu bewateren",
            description: "Start direct bewatering voor alle zones met een gekoppelde entiteit. Overslaanvoorwaarden worden genegeerd.",
            button_all: "Alle zones nu starten",
            no_linked_zones: "Geen zones hebben een gekoppelde schakelaar/klep-entiteit met berekende duur."
          }
        }
      },
      setup: {
        title: "Instellen"
      }
    },
    la = "Smart Irrigation",
    da = {
      title: "Locatie Coördinaten",
      description: "Configureer locatie coördinaten voor het ophalen van weergegevens. Je kunt handmatige coördinaten gebruiken die verschillen van je Home Assistant locatie indien nodig.",
      manual_enabled: "Handmatige coördinaten gebruiken",
      use_ha_location: "Home Assistant locatie gebruiken",
      latitude: "Breedtegraad (decimale graden)",
      longitude: "Lengtegraad (decimale graden)",
      elevation: "Hoogte (meters boven zeeniveau)",
      current_ha_coords: "Huidige Home Assistant coördinaten"
    },
    ua = {
      title: "Dagen tussen bewatering",
      description: "Stel het minimum aantal dagen in tussen bewateringsgebeurtenissen.",
      label: "Minimum dagen tussen bewatering",
      help_text: "Stel in op 0 om uit te schakelen. Waarden van 1-365 dagen worden ondersteund."
    },
    ca = {
      title: "Irrigatiestart-triggers",
      description: "Configureer wanneer de irrigatie moet starten op basis van zonne-evenementen. Je kunt meerdere triggers toevoegen voor verschillende schema's. Voor zonsopkomst-triggers gebruikt een offset van 0 automatisch de totale duur van alle ingeschakelde zones.",
      add_trigger: "Trigger toevoegen",
      edit_trigger: "Trigger bewerken",
      delete_trigger: "Trigger verwijderen",
      trigger_types: {
        sunrise: "Zonsopkomst",
        sunset: "Zonsondergang",
        solar_azimuth: "Zonsazimut"
      },
      fields: {
        name: {
          name: "Triggernaam",
          description: "Een beschrijvende naam om deze trigger te identificeren"
        },
        type: {
          name: "Triggertype",
          description: "Het type zonne-evenement om op te triggeren"
        },
        enabled: {
          name: "Ingeschakeld",
          description: "Of deze trigger momenteel actief is"
        },
        offset_minutes: {
          name: "Offset (minuten)",
          description: "Minuten voor (-) of na (+) het zonne-evenement. Gebruik voor zonsopkomst-triggers 0 voor automatische timing op basis van de totale zoneduur."
        },
        azimuth_angle: {
          name: "Azimuthoek (graden)",
          description: "Zonsazimuthoek in graden waarbij 0=Noord, 90=Oost, 180=Zuid, 270=West"
        },
        account_for_duration: {
          name: "Rekening houden met duur",
          description: "Indien ingeschakeld start de irrigatie vroeg genoeg om op het opgegeven tijdstip klaar te zijn. Indien uitgeschakeld start de irrigatie precies op het opgegeven tijdstip."
        }
      },
      dialog: {
        add_title: "Irrigatiestart-trigger toevoegen",
        edit_title: "Irrigatiestart-trigger bewerken",
        cancel: "Annuleren",
        save: "Opslaan",
        delete: "Verwijderen"
      },
      no_triggers: "Geen irrigatiestart-triggers geconfigureerd. Het systeem gebruikt het standaardgedrag (zonsopkomst met de totale zoneduur). Voeg triggers toe om aan te passen wanneer de irrigatie start.",
      offset_auto: "Automatisch (berekend uit de totale zoneduur)",
      confirm_delete: "Weet je zeker dat je de trigger '{name}' wilt verwijderen?",
      validation: {
        name_required: "Triggernaam is verplicht",
        azimuth_invalid: "De azimuthoek moet een geldig getal zijn"
      },
      help: {
        sunrise_offset: "Voor zonsopkomst-triggers: gebruik negatieve waarden om vóór zonsopkomst te starten, positieve om erna te starten. Zet op 0 om automatisch vroeg genoeg te starten om alle zones vóór zonsopkomst te voltooien.",
        sunset_offset: "Voor zonsondergang-triggers: gebruik negatieve waarden om vóór zonsondergang te starten, positieve om na zonsondergang te starten.",
        azimuth_explanation: "De zonsazimut is de kompasrichting van de zon. 0°=Noord, 90°=Oost, 180°=Zuid, 270°=West. Je kunt elke hoekwaarde invoeren (bijv. 450° = 90°, -30° = 330°). Gebruik dit om de irrigatie te triggeren wanneer de zon een specifieke positie bereikt.",
        multiple_triggers: "Je kunt meerdere triggers configureren. Elke ingeschakelde trigger plant irrigatiestarts onafhankelijk."
      }
    },
    pa = {
      title: "Overslaanvoorwaarden",
      description: "Sla irrigatie automatisch over als de omstandigheden ongunstig zijn. Neerslag-, temperatuur- en windcontroles vereisen een weerdienst.",
      threshold_label: "Neerslagdrempel",
      threshold_description: "Minimale totale verwachte neerslag (in mm) over het vooruitblik-venster om irrigatie over te slaan.",
      lookahead_label: "Vooruitblik (dagen)",
      lookahead_help: "Hoeveel komende verwachtingsdagen worden opgeteld bij de regencontrole. De verwachting begint morgen (vandaag wordt uitgesloten), dus 1 = alleen de volgende dag, 2 = de volgende twee dagen, enzovoort.",
      temp_section_title: "Overslaan bij lage temperatuur",
      temp_threshold_label: "Overslaan als temperatuur onder",
      wind_section_title: "Overslaan bij hoge windsnelheid",
      wind_threshold_label: "Overslaan als windsnelheid boven",
      rain_sensor_section_title: "Regensensorvoorwaarde",
      rain_sensor_label: "Regensensor-entiteit (optioneel)",
      rain_sensor_placeholder: "bijv. binary_sensor.regen"
    },
    ma = {
      title: "Zone-volgorde",
      description: "Als meerdere zones irrigatie nodig hebben, kies of ze tegelijkertijd of na elkaar worden uitgevoerd. In sequentiële modus wacht het systeem tot elke zone klaar is voordat de volgende start.",
      parallel: "Parallel (alle zones tegelijk)",
      sequential: "Sequentieel (één zone tegelijk)",
      rotating: "Roterend (zones wisselen elkaar af)",
      max_consecutive_duration_label: "Max. aaneengesloten looptijd per zone",
      max_consecutive_duration_unit: "minuten",
      min_absorption_time_label: "Min. absorptietijd tussen runs",
      min_absorption_time_unit: "minuten (0 = uitgeschakeld)"
    },
    ga = {
      title: "Weerdienst",
      description: "Configureer welke weerdienst gebruikt wordt voor ET-berekeningen en overslaan-voorwaarden.",
      enabled_label: "Weerdienst inschakelen",
      service_label: "Weerdienst",
      api_key_label: "API-sleutel",
      api_key_placeholder: "Laat leeg om de bestaande sleutel te behouden",
      api_key_configured: "API-sleutel is geconfigureerd",
      api_key_not_configured: "Geen API-sleutel geconfigureerd",
      api_key_help: "Een API-sleutel van je gekozen weerdienstaanbieder. Open-Meteo vereist geen sleutel. OpenWeatherMap en Pirate Weather bieden beide gratis niveaus.",
      no_api_key_needed: "Open-Meteo is een gratis dienst en vereist geen API-sleutel.",
      save_button: "Weerinstellingen opslaan",
      saved: "Weerinstellingen opgeslagen",
      openmeteo: "Open-Meteo (gratis, geen sleutel nodig)",
      test_button: "Verbinding testen",
      test_button_testing: "Bezig met testen…",
      test_success: "✓ Verbinding geslaagd",
      test_error_invalid_auth: "✗ Ongeldige API-sleutel — controleer of deze correct en actief is",
      test_error_cannot_connect: "✗ Kan geen verbinding maken — controleer je internetverbinding",
      test_error_no_service: "✗ Selecteer eerst een weerdienst",
      test_error_unknown: "✗ Test mislukt — onbekende fout",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    ha = {
      zone_size: "Het totale geïrrigeerde oppervlak van deze zone. Wordt samen met de doorvoer gebruikt om te berekenen hoeveel water per run wordt toegediend.",
      zone_throughput: "Totale waterstroom van je irrigatiesysteem voor deze zone (liter/min in metriek, gal/min in imperiaal). Raadpleeg het gegevensblad van je sproeiers of meet hoe lang het duurt om een bak met bekende inhoud te vullen.",
      zone_drainage_rate: "Hoe snel overtollig water uit de bodem wegloopt als de emmer vol is. Typisch: gazon 50 mm/u, zandgrond 100+ mm/u, klei 10 mm/u.",
      zone_bucket: "Huidig watertekort (negatief) of -overschot (positief) voor deze zone. Irrigatie wordt geactiveerd wanneer de emmer onder de drempel zakt.",
      zone_maximum_bucket: "Maximaal vochtoverschot dat de zone kan vasthouden. Water boven dit niveau wordt als afstroming behandeld. Typische waarde: 50 mm.",
      zone_bucket_threshold: "Irrigatie wordt geactiveerd wanneer de emmer onder deze waarde zakt. Moet 0 of negatief zijn. 0 betekent irrigeren zodra er een tekort is.",
      zone_multiplier: "Schaalfactor toegepast op de berekende duur. Boven 1,0 verhoogt, onder 1,0 verlaagt. Handig voor fijnafstemming zonder fysieke metingen te wijzigen.",
      zone_lead_time: "Extra seconden voordat de irrigatie start. Gebruik dit voor het opwarmen van de pomp of het op druk brengen van het systeem.",
      zone_maximum_duration: "Harde bovengrens voor één enkele irrigatierun in seconden. Voorkomt ongecontroleerd water geven. Standaard: 3600 s (1 uur).",
      zone_linked_entity: "De HA-schakelaar- of klep-entiteit die de waterstroom voor deze zone regelt. Deze entiteit wordt ingeschakeld wanneer de irrigatie draait.",
      zone_flow_sensor: "Optionele sensor die het werkelijke waterdebiet meet. Alleen voor rapportage — heeft geen invloed op duurberekeningen.",
      general_autoupdatedelay: "Seconden om te wachten na het starten van HA voordat de eerste weergegevens worden opgehaald. Geeft andere integraties de kans om eerst te initialiseren.",
      general_sensor_debounce: "Minimale tussentijd in milliseconden tussen sensormetingen om ruis van snel veranderende sensoren weg te filteren.",
      general_calctime: "Tijdstip van de dag waarop de irrigatieduren opnieuw worden berekend uit de verzamelde weergegevens. Formaat: UU:MM (24-uurs).",
      general_cleardatatime: "Tijdstip van de dag waarop oude weergegevens worden gewist. Moet later worden ingesteld dan de berekeningstijd.",
      general_days_between: "Minimum aantal dagen tussen irrigatiebeurten voor dezelfde zone. Zet op 0 om uit te schakelen (irrigeren zodra er een tekort is).",
      general_autoupdateinterval: "Hoe vaak weergegevens worden verzameld. Kies een waarde die verse gegevens afweegt tegen API-limieten.",
      general_precipitation_threshold: "Irrigatie wordt overgeslagen als de totale voorspelde neerslag over het vooruitblik-venster deze hoeveelheid overschrijdt.",
      general_temp_threshold: "Irrigatie wordt overgeslagen als de huidige temperatuur onder deze waarde ligt (bijv. om vorstschade te voorkomen).",
      general_wind_threshold: "Irrigatie wordt overgeslagen als de windsnelheid deze waarde overschrijdt (harde wind vermindert de efficiëntie en veroorzaakt drift)."
    },
    va = {
      title: "Configuratiewizard",
      open_button: "Configuratiewizard",
      close: "Sluiten",
      next: "Volgende",
      back: "Terug",
      finish: "Voltooien",
      skip_step: "Deze stap overslaan",
      step_indicator: "Stap {current} van {total}",
      setup_complete_banner: "Configuratie niet voltooid. Voer de wizard uit om te beginnen.",
      open_wizard: "Wizard openen",
      steps: {
        welcome: {
          title: "Welkom bij Smart Irrigation",
          intro: "Deze wizard leidt je door de vier stappen die nodig zijn om je eerste zone automatisch te laten irrigeren.",
          step1_label: "Weerdienst — waar de weergegevens vandaan komen",
          step2_label: "Berekeningsmodule — hoe de irrigatieduur wordt berekend",
          step3_label: "Sensorgroep — welke gegevensbronnen te gebruiken",
          step4_label: "Zone — je eerste irrigatiezone",
          tip: "Je kunt elke stap overslaan en deze later configureren via het tabblad Instellen."
        },
        weather: {
          title: "Weerdienst",
          description: "Kies hoe je weergegevens ophaalt. Open-Meteo is gratis en vereist geen API-sleutel — de eenvoudigste keuze voor de meeste gebruikers."
        },
        module: {
          title: "Berekeningsmodule",
          description: "Een module berekent hoe lang te irrigeren op basis van evapotranspiratie (ET). De PyETO-module (FAO-56-methode) wordt voor de meeste gebruikers aanbevolen.",
          pick_label: "Moduletype selecteren",
          no_modules: "Geen moduletypen beschikbaar."
        },
        mapping: {
          title: "Sensorgroep",
          description: "Een sensorgroep koppelt elke weervariabele aan een gegevensbron. Stel hieronder de belangrijkste variabelen in — afzonderlijke sensortoewijzingen kun je later verfijnen via het tabblad Instellen → Sensorgroepen.",
          name_label: "Naam van de sensorgroep",
          source_label: "Gegevensbron voor",
          use_weather_service: "Weerdienst",
          use_sensor: "Sensor",
          use_static: "Statische waarde",
          use_none: "Geen / niet gebruikt"
        },
        zone: {
          title: "Eerste zone",
          description: "Een zone is één irrigatiegebied (bijv. gazon, plantenbed). Stel de fysieke eigenschappen in zodat het systeem de juiste irrigatieduur kan berekenen.",
          name_label: "Zonenaam",
          size_label: "Oppervlak",
          throughput_label: "Sproeierdoorvoer",
          entity_label: "Gekoppelde schakelaar of klep",
          entity_placeholder: "bijv. switch.garden_valve",
          module_label: "Berekeningsmodule",
          mapping_label: "Sensorgroep"
        },
        done: {
          title: "Configuratie voltooid!",
          description: "Je eerste zone is klaar. Smart Irrigation berekent nu automatisch de irrigatieduren op basis van weergegevens.",
          next_steps: "Wat je hierna kunt doen:",
          tip1: "Ga naar Zones om de berekende duren en emmerwaarden te bekijken.",
          tip2: "Voeg meer zones toe via het tabblad Zones.",
          tip3: "Verfijn alle instellingen via het tabblad Instellen.",
          go_zones: "Naar Zones",
          go_setup: "Naar Instellen"
        }
      },
      stepper: {
        weather: "Weer",
        module: "Module",
        mapping: "Sensorgroep",
        zone: "Zone"
      },
      confirm_close: {
        body: "Configuratiewizard sluiten? Je voortgang is opgeslagen.",
        keep: "Doorgaan",
        close: "Sluiten"
      }
    },
    _a = {
      common: ia,
      defaults: na,
      module: ra,
      calcmodules: oa,
      panels: sa,
      title: la,
      coordinate_config: da,
      days_between_irrigation: ua,
      irrigation_start_triggers: ca,
      weather_skip: pa,
      zone_sequencing: ma,
      weather_service_config: ga,
      field_help: ha,
      wizard: va
    },
    ba = Object.freeze({
      __proto__: null,
      common: ia,
      defaults: na,
      module: ra,
      calcmodules: oa,
      panels: sa,
      title: la,
      coordinate_config: da,
      days_between_irrigation: ua,
      irrigation_start_triggers: ca,
      weather_skip: pa,
      zone_sequencing: ma,
      weather_service_config: ga,
      field_help: ha,
      wizard: va,
      default: _a
    }),
    fa = {
      actions: {
        delete: "Slett",
        edit: "Rediger",
        save: "Lagre",
        cancel: "Avbryt",
        confirm_delete: "Bekreft sletting",
        confirm_delete_zone: "Er du sikker på at du vil slette denne sonen?"
      },
      labels: {
        module: "Modul",
        no: "Nei",
        select: "Velg",
        yes: "Ja",
        enabled: "Aktivert",
        disabled: "Deaktivert",
        before: "før",
        after: "etter",
        settings: "Innstillinger",
        bulk_actions: "Masseoperasjoner"
      },
      attributes: {
        size: "størrelse",
        throughput: "kapasitet",
        state: "status",
        bucket: "beholder",
        last_updated: "sist oppdatert",
        last_calculated: "sist beregnet",
        number_of_data_points: "antall datapunkter"
      },
      loading: "Laster",
      saving: "Lagrer",
      units: {
        seconds: "sekunder"
      },
      "loading-messages": {
        configuration: "Laster konfigurasjon...",
        modules: "Laster moduler...",
        general: "Laster..."
      },
      "saving-messages": {
        adding: "Legger til...",
        saving: "Lagrer..."
      },
      errors: {
        load_failed: "Kunne ikke laste data",
        save_failed: "Kunne ikke lagre endringene",
        delete_failed: "Kunne ikke slette",
        action_failed: "Handlingen mislyktes"
      }
    },
    ka = {
      "default-zone": "Standard sone",
      "default-mapping": "Standard sensorguppe"
    },
    za = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Merk: Denne forklaringen bruker '.' som desimaltegn og viser avrundede verdier. Modulen returnerte evapotranspirasjonsunderskudd på",
          "bucket-was": "Bucket var",
          "new-bucket-values-is": "Ny bucket verdien er",
          "old-bucket-variable": "gammel_bucket",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Siden bucket < 0, Vanning er nødvendig.",
          "steps-taken-to-calculate-duration": "For å beregne nøyaktig varighet, ble følgende trinn utført",
          "precipitation-rate-defined-as": "Nedbørshastigheten er definert som",
          "duration-is-calculated-as": "Varigheten beregnes som",
          bucket: "bøtte",
          "precipitation-rate-variable": "nedbørshastighet",
          "multiplier-is-applied": "Nå blir multiplikatoren brukt. Multiplikatoren er",
          "duration-after-multiplier-is": "derfor er varigheten",
          "maximum-duration-is-applied": "Deretter blir den maksimale varigheten brukt. Den maksimale varigheten er",
          "duration-after-maximum-duration-is": "derfor er varigheten",
          "lead-time-is-applied": "Til slutt blir ledetiden brukt. Ledetiden er",
          "duration-after-lead-time-is": "derfor er den endelige varigheten",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Siden bucket >= 0, Ingen vanning er nødvendig, og varigheten er satt til",
          "maximum-bucket-is": "maksimum bucket stærrelse er",
          "max-bucket-variable": "max_bucket",
          drainage: "drenering",
          "drainage-rate": "dreneringsrate",
          hours: "timer",
          "drainage-rate-is": "Dreneringshastigheten ved metning (beholder på maks) er",
          "current-drainage-is": "Gjeldende drenering beregnet som",
          "no-drainage": "Gjeldende drenering er 0 fordi"
        }
      }
    },
    ya = {
      pyeto: {
        description: "Beregn varigheten basert på FAO56-beregningen fra PyETO-biblioteket"
      },
      static: {
        description: "'Dummy'-modul med en statisk konfigurerbar endring (delta)"
      },
      passthrough: {
        description: "En 'Passthrough'-modul som returnerer verdien av en Evapotranspiration-sensor som delta"
      }
    },
    wa = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Automatisk varighetsberegning",
            labels: {
              "auto-calc-enabled": "Beregn sonevarigheter automatisk",
              "auto-calc-time": "Beregn ved",
              "calc-time": "Beregn kl."
            },
            description: "Beregningen bruker værdataene som er samlet inn frem til da, og oppdaterer bøtten for hver automatiske sone. Deretter justeres varigheten basert på den nye bøtteverdien, og de innsamlede værdataene fjernes."
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Advarsel: Oppdateringstidspunkt for værdata på eller etter beregningstidspunktet"
            },
            header: "Automatisk oppdatering av værdata",
            labels: {
              "auto-update-enabled": "Oppdater værdata automatisk",
              "auto-update-first-update": "(Første) Oppdatering kl",
              "auto-update-interval": "Oppdater sensordata hvert",
              "auto-update-schedule": "Oppdateringsplan",
              "auto-update-time": "Oppdater kl.",
              "auto-update-delay": "Oppdateringsforsinkelse"
            },
            options: {
              days: "dager",
              hours: "timer",
              minutes: "minutter"
            },
            description: "Samle inn og lagre værdata automatisk. Værdata kreves for å beregne sonebøtter og varigheter."
          },
          "automatic-clear": {
            header: "Automatisk rydding av værdata",
            description: "Fjern innsamlede værdata automatisk på et konfigurert tidspunkt. Bruk dette for å sikre at det ikke er igjen værdata fra tidligere dager. Ikke fjern værdataene før du beregner, og bruk bare dette alternativet hvis du forventer at den automatiske oppdateringen samler inn værdata etter at du har beregnet for dagen. Ideelt sett rydder du så sent på dagen som mulig.",
            labels: {
              "automatic-clear-enabled": "Tøm innsamlede værdata automatisk",
              "automatic-clear-time": "Tøm værdata kl."
            }
          },
          continuousupdates: {
            header: "Kontinuerlige sensoroppdateringer (eksperimentell)",
            description: "Eksperimentell funksjon for mer granulære værdata.",
            labels: {
              continuousupdates: "Aktiver kontinuerlige oppdateringer",
              sensor_debounce: "Sensor-debounce",
              "sensor-debounce": "Sensor-debouncetid (ms)"
            }
          }
        },
        description: "Denne siden gir globale innstillinger.",
        title: "Generelt",
        sections: {
          weather: "Vær",
          automation: "Automatisering",
          location: "Plassering",
          watering: "Vanningsatferd"
        }
      },
      help: {
        title: "Hjelp",
        cards: {
          "how-to-get-help": {
            title: "Hvordan få hjelp",
            "first-read-the": "Først, les",
            wiki: "Dokumentasjon",
            "if-you-still-need-help": "Hvis du fremdeles trenger hjelp, ta kontakt på",
            "community-forum": "Fellesskapsforumet",
            "or-open-a": "eller åpne en",
            "github-issue": "Github-sak",
            "english-only": "Kun på engelsk"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Legg til sensorguppe"
            },
            header: "Legg til sensorgupper"
          },
          mapping: {
            aggregates: {
              average: "Gjennomsnitt",
              first: "Første",
              last: "Siste",
              maximum: "Maksimum",
              median: "Median",
              minimum: "Minimum",
              sum: "Sum",
              riemannsum: "Riemann-sum",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Du kan ikke slette denne sensorguppen fordi minst én sone bruker den.",
              invalid_source: "Ugyldig kilde",
              source_does_not_exist: "Kilden finnes ikke. Angi en gyldig kilde, for eksempel 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Duggpunkt",
              evapotranspiration: "Evapotranspirasjon",
              humidity: "Luftfuktighet",
              "maximum temperature": "Maksimumstemperatur",
              "minimum temperature": "Minimumstemperatur",
              precipitation: "Total nedbør",
              pressure: "Trykk",
              "solar radiation": "Solstråling",
              temperature: "Temperatur",
              windspeed: "Vindhastighet",
              "current precipitation": "Nåværende nedbør"
            },
            "sensor-aggregate-of-sensor-values-to-calculate": "av sensordata for å beregne varighet",
            "sensor-aggregate-use-the": "Bruk",
            "sensor-entity": "Sensorenhet",
            static_value: "Verdi",
            "input-units": "Inndata gir verdier i",
            source: "Kilde",
            sources: {
              none: "Ingen",
              weather_service: "Værtjeneste",
              sensor: "Sensor",
              static: "Statisk verdi"
            },
            pressure_types: {
              absolute: "absolutt",
              relative: "relativ"
            },
            "pressure-type": "Trykket er"
          }
        },
        description: "Legg til en eller flere sensorgupper som henter værdata fra Weather service, fra sensorer eller en kombinasjon av disse. Du kan tilordne hver sensorguppe til en eller flere soner",
        labels: {
          "mapping-name": "Navn"
        },
        no_items: "Det er ingen definerte sensorgupper ennå.",
        title: "Sensorgupper",
        "weather-records": {
          title: "Værregistreringer",
          timestamp: "Tid",
          temperature: "Temp.",
          humidity: "Humidity",
          precipitation: "Nedbør",
          "retrieval-time": "Hentet",
          "no-data": "Ingen værdata tilgjengelig for denne sensorgruppen",
          dewpoint: "Dugg",
          wind: "Vind",
          pressure: "Trykk"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Legg til modul"
            },
            header: "Legg til modul"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Du kan ikke slette denne modulen fordi minst én sone bruker den."
            },
            labels: {
              configuration: "Konfigurasjon",
              required: "indikerer et obligatorisk felt"
            },
            "translated-options": {
              DontEstimate: "Ikke beregn",
              EstimateFromSunHours: "Beregn fra soltimer",
              EstimateFromTemp: "Beregn fra temperatur",
              EstimateFromSunHoursAndTemperature: "Estimer fra gjennomsnittet av soltimer og temperatur"
            }
          }
        },
        description: "Legg til en eller flere moduler som beregner vanningsvarighet. Hver modul har sin egen konfigurasjon og kan brukes til å beregne varighet for en eller flere soner.",
        no_items: "Det er ingen definerte moduler ennå.",
        title: "Moduler"
      },
      zones: {
        actions: {
          add: "Legg til",
          calculate: "Beregn",
          information: "Informasjon",
          update: "Oppdater",
          "reset-bucket": "Nullstill bøtte",
          "view-weather-info": "Se værdata",
          "view-weather-info-message": "Værdata tilgjengelig for",
          "view-watering-calendar": "Vanningskalender",
          irrigate_all: "Vann alle soner nå",
          open_settings: "Rediger innstillinger"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Legg til sone"
            },
            header: "Legg til sone"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Beregn varigheter på nytt",
              "update-all": "Oppdater værdata",
              "reset-all-buckets": "Nullstill alle bøtter",
              "clear-all-weatherdata": "Tøm alle værdata"
            },
            header: "Handlinger på alle soner"
          }
        },
        description: "Spesifiser en eller flere vanningssoner her. Vanningens varighet beregnes per sone, avhengig av størrelse, gjennomstrømning, tilstand, modul og sensorguppe.",
        labels: {
          bucket: "Bøtte",
          duration: "Varighet",
          "lead-time": "Ledetid",
          mapping: "Sensorguppe",
          "maximum-duration": "Maksimal varighet",
          multiplier: "Multiplikator",
          name: "Navn",
          size: "Størrelse",
          state: "Tilstand",
          states: {
            automatic: "Automatisk",
            disabled: "Deaktivert",
            manual: "Manuell"
          },
          throughput: "Gjennomstrømning",
          "maximum-bucket": "Maksimal bøtte",
          last_calculated: "Sist beregnet",
          "data-last-updated": "Data sist oppdatert",
          "data-number-of-data-points": "Antall datapunkter",
          drainage_rate: "Dreneringsrate",
          linked_entity: "Tilknyttet bryter/ventil-enhet",
          linked_entity_placeholder: "f.eks. switch.hage_ventil",
          irrigate_now: "Vann nå",
          bucket_threshold: "Minimum underskudd for vanning",
          flow_sensor: "Strømningsmåler-sensor (valgfritt)",
          flow_sensor_placeholder: "f.eks. sensor.zone_flow_rate"
        },
        no_items: "Det er ingen definerte soner ennå.",
        title: "Soner",
        confirm_irrigate: {
          title: "Starte vanning?",
          body: "Dette åpner nå de tilkoblede ventilene og overstyrer alle hoppe-over-betingelser (regn, temperatur, minste antall dager mellom vanninger).",
          all_linked_zones: "Alle tilkoblede soner",
          toast_started: "Vanning startet",
          toast_failed: "Vanning mislyktes"
        },
        status: {
          decision_disabled: "Avslått — denne sonen vannes ikke automatisk.",
          decision_water: "Vanning nødvendig: omtrent {duration} ved neste planlagte kjøring.",
          decision_water_at: "Vanner omtrent {duration} kl. {time}.",
          decision_water_skip: "Underskudd ~{duration}, men neste kjøring blir trolig hoppet over ({reason}).",
          decision_water_no_schedule: "Underskudd ~{duration} — ingen tidsplan vanner denne sonen; start den manuelt.",
          decision_no_water: "Ingen vanning nødvendig nå — jorda har nok fuktighet.",
          decision_unknown: "Ikke beregnet ennå — trykk Oppdater og deretter Beregn for å sjekke.",
          last_checked: "Sist sjekket",
          never: "aldri",
          saved: "Lagret",
          estimate_now: "Nå",
          estimate_tag: "est.",
          estimate_method: {
            hourly: "Sanntidsestimat fra timesvær siden forrige beregning",
            proxy: "Estimat fordelt fra dagens varsel siden forrige beregning"
          }
        },
        help: {
          bucket: "Jordfuktighetsbalanse (bøtte). En negativ verdi betyr at jorda er tørr og sonen trenger vann.",
          calculate: "Beregner hvor lenge det skal vannes ut fra de nyeste dataene. Kjør dette etter Oppdater.",
          update: "Henter de nyeste vær-/sensordataene for denne sonen.",
          irrigate_link_entity: "Koble en bryter/ventil i sonens innstillinger for å aktivere manuell vanning.",
          irrigate_all: "Åpner nå de tilkoblede ventilene for hver sone med underskudd. Hoppe-over-betingelser (regn, vind, temperatur) ignoreres.",
          update_all: "Henter de nyeste vær-/sensordataene for alle soner. Endrer ikke varighetene i seg selv.",
          calculate_all: "Beregner vanningsvarigheten for hver automatisk sone på nytt ut fra dataene som er samlet så langt."
        },
        outlook: {
          next_run: "Neste kjøring",
          no_schedule: "Ingen automatisk tidsplan — soner vannes bare når du starter dem.",
          setup_schedule: "Sett opp en tidsplan",
          targets_all: "alle soner",
          targets_zones: "{count} soner",
          will_skip: "Neste kjøring blir trolig hoppet over",
          will_run: "Forholdene ser klare ut for neste kjøring.",
          why_skipped: "Hvorfor?",
          provisional: "varsel — kan endre seg",
          active_guards: "Aktive betingelser",
          last_run: "Forrige kjøring",
          last_run_skipped: "hoppet over",
          last_run_ran: "kjørt",
          today: "i dag",
          tomorrow: "i morgen",
          actions: {
            irrigate: "Vann",
            calculate: "Beregn på nytt",
            update: "Oppdater data"
          },
          checks: {
            precipitation: "Regnvarsel",
            days_between: "Dager mellom vanninger",
            temperature: "Lav temperatur",
            wind: "Sterk vind",
            rain_sensor: "Regnsensor"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} dager",
            temperature: "{observed}° (under {threshold}°)",
            wind: "{observed} (over {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Ingen vanningskalenderdata tilgjengelig for denne sonen.",
          error_prefix: "Feil ved generering av kalender:",
          month: "Måned",
          et: "ET (mm)",
          precipitation: "Nedbør (mm)",
          watering: "Vanning (L)",
          avg_temp: "Gj.sn. temp. (°C)",
          method_prefix: "Metode:"
        },
        confirm_action: {
          reset_bucket_title: "Nullstille bøtta for denne sonen?",
          reset_bucket_body: "Dette setter bøtta tilbake til 0 og forkaster den oppsamlede fuktighetsbalansen for denne sonen.",
          reset_all_buckets_title: "Nullstille alle bøtter?",
          reset_all_buckets_body: "Dette setter bøtta for hver sone tilbake til 0 og forkaster den oppsamlede fuktighetsbalansen. Vanningsberegningene starter på nytt ved neste oppdatering.",
          clear_weather_title: "Slette alle værdata?",
          clear_weather_body: "Dette sletter alle innsamlede vær- og sensordata for alle soner. Sonene trenger nye data før de kan beregne igjen."
        }
      },
      title: "Smart vanning",
      schedules: {
        title: "Tidsplaner",
        description: "Opprett gjentakende tidsplaner for automatisk beregning, oppdatering eller vanning — uten automatiseringer.",
        add: "Legg til tidsplan",
        no_items: "Ingen tidsplaner konfigurert ennå. Klikk på 'Legg til tidsplan'.",
        zones_all: "Alle soner",
        zones_specific: "Spesifikke soner",
        hours: "timer",
        minutes: "min",
        types: {
          daily: "Daglig",
          weekly: "Ukentlig",
          monthly: "Månedlig",
          interval: "Hver N time",
          sunrise: "Soloppgang",
          sunset: "Solnedgang",
          solar_azimuth: "Solazimutt"
        },
        actions: {
          calculate: "Beregn (oppdater vanningsvarighet)",
          update: "Oppdater (samle inn værdata)",
          irrigate: "Vann (styr ventiler direkte)"
        },
        days: {
          monday: "Ma",
          tuesday: "Ti",
          wednesday: "On",
          thursday: "To",
          friday: "Fr",
          saturday: "Lø",
          sunday: "Sø"
        },
        fields: {
          name: "Navn",
          type: "Tidsplantype",
          enabled: "Aktivert",
          time: "Tid (HH:MM)",
          days_of_week: "Ukedager",
          day_of_month: "Dag i måneden",
          interval_hours: "Intervall",
          action: "Handling",
          zones: "Soner",
          start_date: "Startdato (valgfritt)",
          end_date: "Sluttdato (valgfritt)",
          offset_minutes: "Forskyvning fra soloppgang/-nedgang",
          account_for_duration: "Start tidlig slik at vanningen er ferdig til måltidspunktet",
          azimuth_angle: "Solazimutt-vinkel",
          time_anchor: "Tidspunktet angir"
        },
        dialog: {
          add_title: "Legg til tidsplan",
          edit_title: "Rediger tidsplan"
        },
        time_anchor: {
          start: "Start på vanningen",
          finish: "Slutt på vanningen"
        }
      },
      info: {
        title: "Info",
        description: "Vis informasjon om neste vanning og systemstatus.",
        "configuration-not-available": "Konfigurasjon ikke tilgjengelig.",
        cards: {
          "zone-bucket-values": {
            title: "Sone-beholderverdier og varighet",
            labels: {
              bucket: "Beholder",
              duration: "Varighet"
            },
            "no-zones": "Ingen soner konfigurert"
          },
          "next-irrigation": {
            title: "Neste vanning",
            labels: {
              "next-start": "Neste start",
              duration: "Varighet",
              zones: "Soner"
            },
            "no-data": "Ingen data tilgjengelig"
          },
          "irrigation-reason": {
            title: "Årsak til vanning",
            labels: {
              reason: "Årsak",
              sunrise: "Soloppgang",
              "total-duration": "Total varighet",
              explanation: "Forklaring"
            },
            "no-data": "Ingen data tilgjengelig"
          },
          irrigate_now: {
            title: "Vann nå",
            description: "Start vanning umiddelbart for alle soner med tilknyttet enhet. Hoppover-betingelser ignoreres.",
            button_all: "Start alle soner nå",
            no_linked_zones: "Ingen soner har en tilknyttet bryter/ventil-enhet med beregnet varighet."
          }
        }
      },
      setup: {
        title: "Oppsett"
      }
    },
    Aa = {
      title: "Stedskoordinater",
      description: "Konfigurer stedskoordinater for innhenting av værdata. Du kan bruke manuelle koordinater som er forskjellige fra din Home Assistant plassering om nødvendig.",
      manual_enabled: "Bruk manuelle koordinater",
      use_ha_location: "Bruk Home Assistant plassering",
      latitude: "Breddegrad (desimalgrader)",
      longitude: "Lengdegrad (desimalgrader)",
      elevation: "Høyde (meter over havet)",
      current_ha_coords: "Gjeldende Home Assistant koordinater"
    },
    Sa = {
      title: "Dager mellom vanning",
      description: "Konfigurer minimumsantall dager mellom vanningshendelser.",
      label: "Minimum dager mellom vanning",
      help_text: "Sett til 0 for å deaktivere. Verdier fra 1-365 dager støttes."
    },
    Ea = "Smart Irrigation",
    xa = {
      title: "Utløsere for vanningsstart",
      description: "Konfigurer når vanningen skal starte basert på solhendelser. Du kan legge til flere utløsere for ulike tidsplaner. For soloppgangsutløsere vil et forskyvning på 0 automatisk bruke den totale varigheten av alle aktiverte soner.",
      add_trigger: "Legg til utløser",
      edit_trigger: "Rediger utløser",
      delete_trigger: "Slett utløser",
      trigger_types: {
        sunrise: "Soloppgang",
        sunset: "Solnedgang",
        solar_azimuth: "Solazimut"
      },
      fields: {
        name: {
          name: "Utløsernavn",
          description: "Et beskrivende navn for å identifisere denne utløseren"
        },
        type: {
          name: "Utløsertype",
          description: "Typen solhendelse å utløse på"
        },
        enabled: {
          name: "Aktivert",
          description: "Om denne utløseren er aktiv nå"
        },
        offset_minutes: {
          name: "Forskyvning (minutter)",
          description: "Minutter før (-) eller etter (+) solhendelsen. For soloppgangsutløsere, bruk 0 for automatisk timing basert på total sonevarighet."
        },
        azimuth_angle: {
          name: "Azimutvinkel (grader)",
          description: "Solazimutvinkel i grader der 0=Nord, 90=Øst, 180=Sør, 270=Vest"
        },
        account_for_duration: {
          name: "Ta hensyn til varighet",
          description: "Når aktivert starter vanningen tidlig nok til å bli ferdig til angitt tidspunkt. Når deaktivert starter vanningen nøyaktig på angitt tidspunkt."
        }
      },
      dialog: {
        add_title: "Legg til utløser for vanningsstart",
        edit_title: "Rediger utløser for vanningsstart",
        cancel: "Avbryt",
        save: "Lagre",
        delete: "Slett"
      },
      no_triggers: "Ingen utløsere for vanningsstart konfigurert. Systemet bruker standardatferden (soloppgang med total sonevarighet). Legg til utløsere for å tilpasse når vanningen starter.",
      offset_auto: "Automatisk (beregnet fra total sonevarighet)",
      confirm_delete: "Er du sikker på at du vil slette utløseren '{name}'?",
      validation: {
        name_required: "Utløsernavn er påkrevd",
        azimuth_invalid: "Azimutvinkelen må være et gyldig tall"
      },
      help: {
        sunrise_offset: "For soloppgangsutløsere: Bruk negative verdier for å starte før soloppgang, positive for å starte etter. Sett til 0 for automatisk å starte tidlig nok til å fullføre alle soner før soloppgang.",
        sunset_offset: "For solnedgangsutløsere: Bruk negative verdier for å starte før solnedgang, positive for å starte etter solnedgang.",
        azimuth_explanation: "Solazimut er kompassretningen til solen. 0°=Nord, 90°=Øst, 180°=Sør, 270°=Vest. Du kan angi en hvilken som helst vinkelverdi (f.eks. 450° = 90°, -30° = 330°). Bruk dette til å utløse vanning når solen når en bestemt posisjon.",
        multiple_triggers: "Du kan konfigurere flere utløsere. Hver aktiverte utløser planlegger vanningsstart uavhengig."
      }
    },
    Ta = {
      title: "Hoppover-betingelser",
      description: "Hopp automatisk over vanning når forholdene er ugunstige. Nedbørs-, temperatur- og vindsjekker krever en værtjeneste.",
      threshold_label: "Nedbørsterskel",
      threshold_description: "Minimum total forventet nedbør (i mm) over varslingsvinduet for å hoppe over vanning.",
      lookahead_label: "Varslingsvindu (dager)",
      lookahead_help: "Hvor mange kommende varseldøgn som summeres ved regnsjekken. Varselet starter i morgen (i dag utelates), så 1 = bare neste dag, 2 = de neste to dagene, og så videre.",
      temp_section_title: "Hopp over ved lav temperatur",
      temp_threshold_label: "Hopp over hvis temperatur under",
      wind_section_title: "Hopp over ved sterk vind",
      wind_threshold_label: "Hopp over hvis vindhastighet over",
      rain_sensor_section_title: "Regnsensorbetingelse",
      rain_sensor_label: "Regnsensor-enhet (valgfritt)",
      rain_sensor_placeholder: "f.eks. binary_sensor.regn"
    },
    ja = {
      title: "Sonesekvens",
      description: "Når flere soner trenger vanning, velg om de kjører samtidig eller én etter én. I sekvensiell modus venter systemet til hver sone er ferdig før neste starter.",
      parallel: "Parallell (alle soner samtidig)",
      sequential: "Sekvensiell (én sone om gangen)",
      rotating: "Roterende (soner bytter på)",
      max_consecutive_duration_label: "Maks. sammenhengende kjøretid per sone",
      max_consecutive_duration_unit: "minutter",
      min_absorption_time_label: "Min. absorpsjonstid mellom økter",
      min_absorption_time_unit: "minutter (0 = deaktivert)"
    },
    Pa = {
      title: "Værtjeneste",
      description: "Konfigurer hvilken værtjeneste som skal brukes for ET-beregninger og hopp over-betingelser.",
      enabled_label: "Aktiver værtjeneste",
      service_label: "Værtjeneste",
      api_key_label: "API-nøkkel",
      api_key_placeholder: "La stå tom for å beholde eksisterende nøkkel",
      api_key_configured: "API-nøkkel er konfigurert",
      api_key_not_configured: "Ingen API-nøkkel konfigurert",
      api_key_help: "En API-nøkkel fra den valgte værtjenesteleverandøren din. Open-Meteo krever ingen nøkkel. OpenWeatherMap og Pirate Weather tilbyr begge gratis nivåer.",
      no_api_key_needed: "Open-Meteo er en gratis tjeneste og krever ingen API-nøkkel.",
      save_button: "Lagre værinnstillinger",
      saved: "Værinnstillinger lagret",
      openmeteo: "Open-Meteo (gratis, ingen nøkkel nødvendig)",
      test_button: "Test tilkobling",
      test_button_testing: "Tester…",
      test_success: "✓ Tilkobling vellykket",
      test_error_invalid_auth: "✗ Ugyldig API-nøkkel — sjekk at den er riktig og aktiv",
      test_error_cannot_connect: "✗ Kan ikke koble til — sjekk internettforbindelsen din",
      test_error_no_service: "✗ Velg en værtjeneste først",
      test_error_unknown: "✗ Test mislyktes — ukjent feil",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    Ma = {
      zone_size: "Det totale vannede arealet for denne sonen. Brukes sammen med gjennomstrømningen for å beregne hvor mye vann som tilføres per kjøring.",
      zone_throughput: "Total vanngjennomstrømning for vanningssystemet ditt for denne sonen (liter/min i metrisk, gal/min i imperisk). Sjekk databladet for sprederne dine eller mål ved å ta tiden på hvor lang tid det tar å fylle en beholder med kjent volum.",
      zone_drainage_rate: "Hvor raskt overflødig vann dreneres fra jorden når bøtten er full. Typisk: plen 50 mm/t, sandjord 100+ mm/t, leire 10 mm/t.",
      zone_bucket: "Nåværende vannunderskudd (negativt) eller -overskudd (positivt) for denne sonen. Vanning utløses når bøtten faller under terskelen.",
      zone_maximum_bucket: "Maksimalt fuktoverskudd sonen kan holde på. Vann over dette nivået behandles som avrenning. Typisk verdi: 50 mm.",
      zone_bucket_threshold: "Vanning utløses når bøtten faller under denne verdien. Må være 0 eller negativ. 0 betyr å vanne så snart det er et underskudd.",
      zone_multiplier: "Skaleringsfaktor som brukes på den beregnede varigheten. Over 1,0 øker, under 1,0 reduserer. Nyttig for finjustering uten å endre fysiske målinger.",
      zone_lead_time: "Ekstra sekunder før vanningen starter. Bruk dette for oppvarming av pumpen eller trykksetting av systemet.",
      zone_maximum_duration: "Hard øvre grense for én enkelt vanningskjøring i sekunder. Hindrer ukontrollert vanning. Standard: 3600 s (1 time).",
      zone_linked_entity: "HA-bryter- eller ventilenheten som styrer vannstrømmen for denne sonen. Denne enheten slås på når vanningen kjører.",
      zone_flow_sensor: "Valgfri sensor som måler faktisk vannstrømningsrate. Brukes bare til rapportering — påvirker ikke varighetsberegninger.",
      general_autoupdatedelay: "Sekunder å vente etter at HA starter før første henting av værdata. Lar andre integrasjoner initialisere først.",
      general_sensor_debounce: "Minimum mellomrom i millisekunder mellom sensoravlesninger for å filtrere bort støy fra raskt skiftende sensorer.",
      general_calctime: "Tidspunkt på dagen da vanningsvarighetene beregnes på nytt fra innsamlede værdata. Format: TT:MM (24-timers).",
      general_cleardatatime: "Tidspunkt på dagen da gamle værdata slettes. Må settes senere enn beregningstidspunktet.",
      general_days_between: "Minimum antall dager mellom vanninger for samme sone. Sett til 0 for å deaktivere (vann så snart det er et underskudd).",
      general_autoupdateinterval: "Hvor ofte værdata samles inn. Velg en verdi som balanserer ferske data mot API-grenser.",
      general_precipitation_threshold: "Vanning hoppes over hvis total varslet nedbør over varslingsvinduet overstiger denne mengden.",
      general_temp_threshold: "Vanning hoppes over hvis nåværende temperatur er under denne verdien (f.eks. for å forhindre frostskade).",
      general_wind_threshold: "Vanning hoppes over hvis vindhastigheten overstiger denne verdien (sterk vind reduserer effektiviteten og forårsaker avdrift)."
    },
    Da = {
      title: "Oppsettsveiviser",
      open_button: "Oppsettsveiviser",
      close: "Lukk",
      next: "Neste",
      back: "Tilbake",
      finish: "Fullfør",
      skip_step: "Hopp over dette trinnet",
      step_indicator: "Trinn {current} av {total}",
      setup_complete_banner: "Oppsett ikke fullført. Kjør veiviseren for å komme i gang.",
      open_wizard: "Åpne veiviser",
      steps: {
        welcome: {
          title: "Velkommen til Smart Irrigation",
          intro: "Denne veiviseren leder deg gjennom de fire trinnene som trengs for å få den første sonen din til å vanne automatisk.",
          step1_label: "Værtjeneste — hvor værdataene hentes fra",
          step2_label: "Beregningsmodul — hvordan vanningsvarigheten beregnes",
          step3_label: "Sensorgruppe — hvilke datakilder som skal brukes",
          step4_label: "Sone — din første vanningssone",
          tip: "Du kan hoppe over et hvilket som helst trinn og konfigurere det senere fra Oppsett-fanen."
        },
        weather: {
          title: "Værtjeneste",
          description: "Velg hvordan værdata hentes. Open-Meteo er gratis og krever ingen API-nøkkel — det enkleste valget for de fleste."
        },
        module: {
          title: "Beregningsmodul",
          description: "En modul beregner hvor lenge det skal vannes basert på evapotranspirasjon (ET). PyETO-modulen (FAO-56-metoden) anbefales for de fleste.",
          pick_label: "Velg modultype",
          no_modules: "Ingen modultyper tilgjengelig."
        },
        mapping: {
          title: "Sensorgruppe",
          description: "En sensorgruppe kobler hver værvariabel til en datakilde. Angi nøkkelvariablene nedenfor — du kan finjustere individuelle sensortilordninger senere fra Oppsett → Sensorgrupper-fanen.",
          name_label: "Navn på sensorgruppe",
          source_label: "Datakilde for",
          use_weather_service: "Værtjeneste",
          use_sensor: "Sensor",
          use_static: "Statisk verdi",
          use_none: "Ingen / ikke brukt"
        },
        zone: {
          title: "Første sone",
          description: "En sone er ett vanningsområde (f.eks. plen, bed). Angi de fysiske egenskapene slik at systemet kan beregne riktig vanningsvarighet.",
          name_label: "Sonenavn",
          size_label: "Areal",
          throughput_label: "Spredergjennomstrømning",
          entity_label: "Tilkoblet bryter eller ventil",
          entity_placeholder: "f.eks. switch.garden_valve",
          module_label: "Beregningsmodul",
          mapping_label: "Sensorgruppe"
        },
        done: {
          title: "Oppsett fullført!",
          description: "Den første sonen din er klar. Smart Irrigation vil nå beregne vanningsvarigheter automatisk basert på værdata.",
          next_steps: "Hva du kan gjøre videre:",
          tip1: "Gå til Soner for å se beregnede varigheter og bøtteverdier.",
          tip2: "Legg til flere soner fra Soner-fanen.",
          tip3: "Finjuster alle innstillinger fra Oppsett-fanen.",
          go_zones: "Gå til Soner",
          go_setup: "Gå til Oppsett"
        }
      },
      stepper: {
        weather: "Vær",
        module: "Modul",
        mapping: "Sensorgruppe",
        zone: "Sone"
      },
      confirm_close: {
        body: "Lukke oppsettsveiviseren? Fremgangen din er lagret.",
        keep: "Fortsett",
        close: "Lukk"
      }
    },
    Ca = {
      common: fa,
      defaults: ka,
      module: za,
      calcmodules: ya,
      panels: wa,
      coordinate_config: Aa,
      days_between_irrigation: Sa,
      title: Ea,
      irrigation_start_triggers: xa,
      weather_skip: Ta,
      zone_sequencing: ja,
      weather_service_config: Pa,
      field_help: Ma,
      wizard: Da
    },
    Ha = Object.freeze({
      __proto__: null,
      common: fa,
      defaults: ka,
      module: za,
      calcmodules: ya,
      panels: wa,
      coordinate_config: Aa,
      days_between_irrigation: Sa,
      title: Ea,
      irrigation_start_triggers: xa,
      weather_skip: Ta,
      zone_sequencing: ja,
      weather_service_config: Pa,
      field_help: Ma,
      wizard: Da,
      default: Ca
    }),
    La = {
      actions: {
        delete: "Zmazať",
        edit: "Upraviť",
        save: "Uložiť",
        cancel: "Zrušiť",
        confirm_delete: "Potvrdiť odstránenie",
        confirm_delete_zone: "Naozaj chceš odstrániť túto zónu?"
      },
      labels: {
        module: "Modul",
        no: "Nie",
        select: "Zvoliť",
        yes: "Áno",
        enabled: "Povolené",
        disabled: "Zakázané",
        before: "pred",
        after: "po",
        settings: "Nastavenia",
        bulk_actions: "Hromadné akcie"
      },
      attributes: {
        size: "veľkosť",
        throughput: "priepustnosť",
        state: "stav",
        bucket: "zásobník",
        last_updated: "posledná aktualizácia",
        last_calculated: "posledný výpočet",
        number_of_data_points: "počet dátových bodov"
      },
      loading: "Načítanie",
      saving: "Ukladanie",
      units: {
        seconds: "sekúnd"
      },
      "loading-messages": {
        configuration: "Načítanie konfigurácie...",
        modules: "Načítanie modulov...",
        general: "Načítanie..."
      },
      "saving-messages": {
        adding: "Pridávanie...",
        saving: "Ukladanie..."
      },
      errors: {
        load_failed: "Údaje sa nepodarilo načítať",
        save_failed: "Zmeny sa nepodarilo uložiť",
        delete_failed: "Nepodarilo sa odstrániť",
        action_failed: "Akcia zlyhala"
      }
    },
    Ba = {
      "default-zone": "Predvolená zóna",
      "default-mapping": "Predvolená skupina snímačov"
    },
    Na = {
      calculation: {
        explanation: {
          "module-returned-evapotranspiration-deficiency": "Poznámka: toto vysvetlenie používa '.' ako oddeľovač desatinných miest zobrazuje zaokrúhlené a metrické hodnoty. Modul vrátil nedostatok evapotranspirácie",
          "bucket-was": "Vedro bolo",
          "new-bucket-values-is": "Hodnota nového vedra je",
          "old-bucket-variable": "staré_vedro",
          delta: "delta",
          "bucket-less-than-zero-irrigation-necessary": "Keďže vedro < 0, je potrebné zavlažovanie",
          "steps-taken-to-calculate-duration": "Na výpočet presného trvania sa vykonali nasledujúce kroky",
          "precipitation-rate-defined-as": "Miera zrážok je definovaná ako",
          "duration-is-calculated-as": "Trvanie sa vypočíta ako",
          bucket: "vedro",
          "precipitation-rate-variable": "úhrn zrážok",
          "multiplier-is-applied": "Teraz sa použije multiplikátor. Násobiteľ je",
          "duration-after-multiplier-is": "teda trvanie je",
          "maximum-duration-is-applied": "Potom sa použije maximálne trvanie. Maximálne trvanie je",
          "duration-after-maximum-duration-is": "teda trvanie je",
          "lead-time-is-applied": "Nakoniec sa použije dodacia lehota. Dodacia lehota je",
          "duration-after-lead-time-is": "teda konečné trvanie je",
          "bucket-larger-than-or-equal-to-zero-no-irrigation-necessary": "Keďže vedro >= 0, nie je potrebné žiadne zavlažovanie a trvanie je nastavené na",
          "maximum-bucket-is": "maximálna veľkosť vedra je",
          "max-bucket-variable": "max_bucket",
          drainage: "odvodnenie",
          "drainage-rate": "miera odvodnenia",
          hours: "hodiny",
          "drainage-rate-is": "Rýchlosť odtoku pri nasýtení (zásobník na maxime) je",
          "current-drainage-is": "Aktuálna drenáž vypočítaná ako",
          "no-drainage": "Aktuálna drenáž je 0, pretože"
        }
      }
    },
    Ia = {
      pyeto: {
        description: "Vypočítajte trvanie na základe výpočtu FAO56 z knižnice PyETO"
      },
      static: {
        description: "'Atrapa' modul so statickou konfigurovateľnou deltou"
      },
      passthrough: {
        description: "Priechodný modul, ktorý vracia hodnotu evapotranspiračného senzora ako delta"
      }
    },
    Oa = {
      general: {
        cards: {
          "automatic-duration-calculation": {
            header: "Automatický výpočet trvania",
            description: "Výpočet berie zhromaždené údaje o počasí až do tohto bodu a aktualizuje vedro pre každú automatickú zónu. Potom sa trvanie upraví na základe novej hodnoty segmentu a zhromaždené údaje o počasí sa odstránia.",
            labels: {
              "auto-calc-enabled": "Automaticky vypočítajte trvanie zón",
              "auto-calc-time": "Vypočítajte pri",
              "calc-time": "Vypočítať o"
            }
          },
          "automatic-update": {
            errors: {
              "warning-update-time-on-or-after-calc-time": "Upozornenie: Čas aktualizácie údajov o počasí v čase výpočtu alebo po ňom"
            },
            header: "Automatická aktualizácia poveternostných údajov",
            description: "Automaticky zbierajte a ukladajte údaje o počasí. Údaje o počasí sú potrebné na výpočet segmentov zón a trvania.",
            labels: {
              "auto-update-enabled": "Automaticky aktualizovať údaje o počasí",
              "auto-update-delay": "Oneskorenie aktualizácie",
              "auto-update-interval": "Aktualizujte údaje snímača každý",
              "auto-update-schedule": "Plán aktualizácie",
              "auto-update-time": "Aktualizovať o"
            },
            options: {
              days: "dni",
              hours: "hodiny",
              minutes: "minúty"
            }
          },
          "automatic-clear": {
            header: "Automatické orezávanie údajov o počasí",
            description: "Automaticky odstráňte zhromaždené údaje o počasí v nakonfigurovanom čase. Použite to, aby ste sa uistili, že nezostali žiadne údaje o počasí z predchádzajúcich dní. Neodstraňujte údaje o počasí pred výpočtom a túto možnosť použite iba vtedy, ak očakávate, že automatická aktualizácia bude zhromažďovať údaje o počasí až po výpočte na daný deň. V ideálnom prípade chcete prerezávať tak neskoro, ako je to možné.",
            labels: {
              "automatic-clear-enabled": "Automaticky vymazať zhromaždené údaje o počasí",
              "automatic-clear-time": "Vymazať údaje o počasí o"
            }
          },
          continuousupdates: {
            header: "Priebežné aktualizácie senzorov (experimentálne)",
            description: "Experimentálna funkcia pre podrobnejšie meteorologické dáta.",
            labels: {
              continuousupdates: "Povoliť priebežné aktualizácie",
              sensor_debounce: "Debounce senzora",
              "sensor-debounce": "Čas odrazu senzora (ms)"
            }
          }
        },
        description: "Táto stránka poskytuje globálne nastavenia.",
        title: "Všeobecné",
        sections: {
          weather: "Počasie",
          automation: "Automatizácia",
          location: "Poloha",
          watering: "Správanie zavlažovania"
        }
      },
      help: {
        title: "Pomoc",
        cards: {
          "how-to-get-help": {
            title: "Ako získať pomoc",
            "first-read-the": "Najprv si prečítajte",
            wiki: "Dokumentácia",
            "if-you-still-need-help": "Ak stále potrebujete pomoc, obráťte sa na",
            "community-forum": "komunitné fórum",
            "or-open-a": "alebo otvorte a",
            "github-issue": "Problém Github",
            "english-only": "len anglicky"
          }
        }
      },
      mappings: {
        cards: {
          "add-mapping": {
            actions: {
              add: "Pridať skupinu snímačov"
            },
            header: "Pridajte skupiny senzorov"
          },
          mapping: {
            aggregates: {
              average: "Priemer",
              first: "Prvý",
              last: "Posledný",
              maximum: "Maximum",
              median: "Medián",
              minimum: "Minimum",
              sum: "Súčet",
              riemannsum: "Riemannova suma",
              delta: "Delta"
            },
            errors: {
              "cannot-delete-mapping-because-zones-use-it": "Túto skupinu senzorov nemôžete vymazať, pretože ju používa aspoň jedna zóna.",
              invalid_source: "Neplatný zdroj",
              source_does_not_exist: "Zdroj neexistuje. Zadaj platný zdroj, napríklad 'sensor.mysensor'."
            },
            items: {
              dewpoint: "Rosný bod",
              evapotranspiration: "Evapotranspirácia",
              humidity: "Vlhkosť",
              "maximum temperature": "Maximálna teplota",
              "minimum temperature": "Minimálna teplota",
              precipitation: "Úhrn zrážok",
              pressure: "Tlak",
              "solar radiation": "Slnečné žiarenie",
              temperature: "Teplota",
              windspeed: "Rýchlosť vetra",
              "current precipitation": "Aktuálne zrážky"
            },
            pressure_types: {
              absolute: "absolútne",
              relative: "relatítne"
            },
            "pressure-type": "Tlak je",
            "sensor-aggregate-of-sensor-values-to-calculate": "hodnôt snímača na výpočet trvania",
            "sensor-aggregate-use-the": "Použiť",
            "sensor-entity": "Entita snímača",
            static_value: "Hodnota",
            "input-units": "Vstup poskytuje hodnoty v",
            source: "Zdroj",
            sources: {
              none: "Nie je",
              weather_service: "Poveternostná služba",
              sensor: "Snímač",
              static: "Statická hodnota"
            }
          }
        },
        description: "Pridajte jednu alebo viac skupín senzorov, ktoré získavajú údaje o počasí z Weather service, zo senzorov alebo ich kombinácie. Každú skupinu senzorov môžete namapovať na jednu alebo viac zón",
        labels: {
          "mapping-name": "Názov"
        },
        no_items: "Zatiaľ nie je definovaná žiadna skupina senzorov.",
        title: "Skupiny senzorov",
        "weather-records": {
          title: "Záznamy o počasí",
          timestamp: "Čas",
          temperature: "Tepl.",
          humidity: "Humidity",
          precipitation: "Zrážky",
          "retrieval-time": "Získané",
          "no-data": "Pre túto skupinu senzorov nie sú dostupné žiadne poveternostné údaje",
          dewpoint: "Rosa",
          wind: "Vietor",
          pressure: "Tlak"
        }
      },
      modules: {
        cards: {
          "add-module": {
            actions: {
              add: "Pridať modul"
            },
            header: "Pridať modul"
          },
          module: {
            errors: {
              "cannot-delete-module-because-zones-use-it": "Tento modul nemôžete vymazať, pretože ho používa aspoň jedna zóna."
            },
            labels: {
              configuration: "Konfigurácia",
              required: "označuje povinné pole"
            },
            "translated-options": {
              DontEstimate: "Bez odhadu",
              EstimateFromSunHours: "Odhad zo slnečných hodín",
              EstimateFromTemp: "Odhad z teploty",
              EstimateFromSunHoursAndTemperature: "Odhad z priemeru hodín slnečného svitu a teploty"
            }
          }
        },
        description: "Pridajte jeden alebo viac modulov, ktoré vypočítavajú trvanie zavlažovania. Každý modul sa dodáva s vlastnou konfiguráciou a možno ho použiť na výpočet trvania pre jednu alebo viac zón.",
        no_items: "Zatiaľ nie sú definované žiadne moduly.",
        title: "Moduly"
      },
      zones: {
        actions: {
          add: "Pridať",
          calculate: "Vypočítať",
          information: "Informácia",
          update: "Aktualizovať",
          "reset-bucket": "Resetovať vedro",
          "view-weather-info": "Zobraziť počasie",
          "view-weather-info-message": "Poveternostné údaje dostupné pre",
          "view-watering-calendar": "Kalendár zavlažovania",
          irrigate_all: "Zavlažiť všetky zóny teraz",
          open_settings: "Upraviť nastavenia"
        },
        cards: {
          "add-zone": {
            actions: {
              add: "Pridať zónu"
            },
            header: "Pridať zónu"
          },
          "zone-actions": {
            actions: {
              "calculate-all": "Prepočítať trvania",
              "update-all": "Obnoviť údaje o počasí",
              "reset-all-buckets": "Obnovte všetky vedrá",
              "clear-all-weatherdata": "Vymazať všetky údaje o počasí"
            },
            header: "Akcie vo všetkých zónach"
          }
        },
        description: "Tu špecifikujte jednu alebo viac zavlažovacích zón. Trvanie zavlažovania sa vypočíta pre zónu v závislosti od veľkosti, výkonu, stavu, modulu a skupiny senzorov.",
        labels: {
          bucket: "Vedro",
          duration: "Trvanie",
          "lead-time": "Dodacia lehota",
          mapping: "Skupina senzorov",
          "maximum-duration": "Maximálne trvanie",
          multiplier: "Násobiteľ",
          name: "Názov",
          size: "Veľkosť",
          state: "Stav",
          states: {
            automatic: "Automatický",
            disabled: "Zakázaný",
            manual: "Manuány"
          },
          throughput: "Priepustnosť",
          "maximum-bucket": "Maximálne vedro",
          last_calculated: "Naposledy vypočítané",
          "data-last-updated": "Údaje boli naposledy aktualizované",
          "data-number-of-data-points": "Počet údajových bodov",
          drainage_rate: "Miera odvodnenia",
          linked_entity: "Prepojená entita prepínača/ventilu",
          linked_entity_placeholder: "napr. switch.zahradny_ventil",
          irrigate_now: "Zavlažiť teraz",
          bucket_threshold: "Minimálny deficit pre závlahu",
          flow_sensor: "Senzor prietokomera (voliteľné)",
          flow_sensor_placeholder: "napr. sensor.zone_flow_rate"
        },
        no_items: "Zatiaľ nie sú definované žiadne zóny.",
        title: "Zóny",
        confirm_irrigate: {
          title: "Spustiť zavlažovanie?",
          body: "Týmto sa teraz otvoria prepojené ventily a obídu sa všetky podmienky preskočenia (dážď, teplota, minimálny počet dní medzi zavlažovaniami).",
          all_linked_zones: "Všetky prepojené zóny",
          toast_started: "Zavlažovanie spustené",
          toast_failed: "Zavlažovanie zlyhalo"
        },
        status: {
          decision_disabled: "Vypnuté — táto zóna sa nebude automaticky zavlažovať.",
          decision_water: "Potrebné zavlažovanie: približne {duration} pri ďalšom plánovanom spustení.",
          decision_water_at: "Zavlaží približne {duration} o {time}.",
          decision_water_skip: "Deficit ~{duration}, ale ďalšie spustenie sa pravdepodobne preskočí ({reason}).",
          decision_water_no_schedule: "Deficit ~{duration} — túto zónu nezavlažuje žiadny plán; spustite ju manuálne.",
          decision_no_water: "Momentálne nie je potrebné zavlažovanie — pôda má dostatok vlhkosti.",
          decision_unknown: "Ešte nevypočítané — stlačte Aktualizovať a potom Vypočítať na kontrolu.",
          last_checked: "Naposledy skontrolované",
          never: "nikdy",
          saved: "Uložené",
          estimate_now: "Teraz",
          estimate_tag: "odh.",
          estimate_method: {
            hourly: "Živý odhad z hodinového počasia od posledného výpočtu",
            proxy: "Odhad rozložený z dnešnej predpovede od posledného výpočtu"
          }
        },
        help: {
          bucket: "Bilancia vlhkosti pôdy (vedro). Záporná hodnota znamená, že pôda je suchá a zóna potrebuje vodu.",
          calculate: "Vypočíta dĺžku zavlažovania z najnovších údajov. Spustite po Aktualizovať.",
          update: "Načíta najnovšie meteorologické/senzorové údaje pre túto zónu.",
          irrigate_link_entity: "Priraďte v nastaveniach tejto zóny spínač/ventil, aby ste umožnili manuálne zavlažovanie.",
          irrigate_all: "Okamžite otvorí prepojené ventily pre každú zónu s deficitom. Podmienky preskočenia (dážď, vietor, teplota) sa ignorujú.",
          update_all: "Zhromaždí najnovšie meteorologické/senzorové údaje pre všetky zóny. Samo o sebe nemení trvania.",
          calculate_all: "Prepočíta trvanie zavlažovania každej automatickej zóny z doteraz zhromaždených údajov."
        },
        outlook: {
          next_run: "Ďalšie spustenie",
          no_schedule: "Žiadny automatický plán — zóny sa zavlažujú len keď ich spustíte.",
          setup_schedule: "Nastaviť plán",
          targets_all: "všetky zóny",
          targets_zones: "{count} zón",
          will_skip: "Ďalšie spustenie sa pravdepodobne preskočí",
          will_run: "Podmienky pre ďalšie spustenie vyzerajú priaznivo.",
          why_skipped: "Prečo?",
          provisional: "predpoveď — môže sa zmeniť",
          active_guards: "Aktívne podmienky",
          last_run: "Posledné spustenie",
          last_run_skipped: "preskočené",
          last_run_ran: "spustené",
          today: "dnes",
          tomorrow: "zajtra",
          actions: {
            irrigate: "Zavlažiť",
            calculate: "Prepočítať",
            update: "Obnoviť údaje"
          },
          checks: {
            precipitation: "Predpoveď dažďa",
            days_between: "Dni medzi zavlažovaniami",
            temperature: "Nízka teplota",
            wind: "Silný vietor",
            rain_sensor: "Senzor dažďa"
          },
          check_detail: {
            precipitation: "{observed} mm (≥ {threshold} mm)",
            days_between: "{observed}/{threshold} dní",
            temperature: "{observed}° (pod {threshold}°)",
            wind: "{observed} (nad {threshold})",
            rain_sensor: "{observed}"
          }
        },
        calendar: {
          no_data: "Pre túto zónu nie sú k dispozícii žiadne údaje kalendára zavlažovania.",
          error_prefix: "Chyba pri generovaní kalendára:",
          month: "Mesiac",
          et: "ET (mm)",
          precipitation: "Zrážky (mm)",
          watering: "Zavlažovanie (L)",
          avg_temp: "Priem. teplota (°C)",
          method_prefix: "Metóda:"
        },
        confirm_action: {
          reset_bucket_title: "Vynulovať vedro tejto zóny?",
          reset_bucket_body: "Týmto sa vedro nastaví späť na 0 a zruší sa nahromadená bilancia vlhkosti pre túto zónu.",
          reset_all_buckets_title: "Vynulovať všetky vedrá?",
          reset_all_buckets_body: "Týmto sa vedro každej zóny nastaví späť na 0 a zruší sa nahromadená bilancia vlhkosti. Výpočty zavlažovania začnú odznova pri ďalšej aktualizácii.",
          clear_weather_title: "Vymazať všetky meteorologické údaje?",
          clear_weather_body: "Týmto sa odstránia všetky zhromaždené meteorologické a senzorové záznamy pre všetky zóny. Zóny budú pred ďalším výpočtom potrebovať nové údaje."
        }
      },
      schedules: {
        title: "Plány",
        description: "Vytvorte opakujúce sa plány pre automatický výpočet, aktualizáciu alebo závlahu — bez automatizácií.",
        add: "Pridať plán",
        no_items: "Zatiaľ nie sú nakonfigurované žiadne plány. Kliknite na 'Pridať plán'.",
        zones_all: "Všetky zóny",
        zones_specific: "Konkrétne zóny",
        hours: "hodín",
        minutes: "min",
        types: {
          daily: "Denne",
          weekly: "Týždenne",
          monthly: "Mesačne",
          interval: "Každých N hodín",
          sunrise: "Východ slnka",
          sunset: "Západ slnka",
          solar_azimuth: "Slnečný azimut"
        },
        actions: {
          calculate: "Vypočítať (aktualizovať dobu závlahy)",
          update: "Aktualizovať (zbierať meteorologické dáta)",
          irrigate: "Zavlažiť (priamo ovládať ventily)"
        },
        days: {
          monday: "Po",
          tuesday: "Ut",
          wednesday: "St",
          thursday: "Št",
          friday: "Pi",
          saturday: "So",
          sunday: "Ne"
        },
        fields: {
          name: "Názov",
          type: "Typ plánu",
          enabled: "Povolené",
          time: "Čas (HH:MM)",
          days_of_week: "Dni v týždni",
          day_of_month: "Deň v mesiaci",
          interval_hours: "Interval",
          action: "Akcia",
          zones: "Zóny",
          start_date: "Dátum začiatku (voliteľné)",
          end_date: "Dátum konca (voliteľné)",
          offset_minutes: "Posun od východu/západu slnka",
          account_for_duration: "Spustiť skoro, aby závlaha skončila v cieľovom čase",
          azimuth_angle: "Uhol slnečného azimutu",
          time_anchor: "Čas označuje"
        },
        dialog: {
          add_title: "Pridať plán",
          edit_title: "Upraviť plán"
        },
        time_anchor: {
          start: "Začiatok zavlažovania",
          finish: "Koniec zavlažovania"
        }
      },
      info: {
        title: "Info",
        description: "Zobraziť informácie o ďalšej závlahe a stave systému.",
        "configuration-not-available": "Konfigurácia nie je k dispozícii.",
        cards: {
          "zone-bucket-values": {
            title: "Hodnoty zásobníka zóny a trvanie",
            labels: {
              bucket: "Zásobník",
              duration: "Trvanie"
            },
            "no-zones": "Žiadne zóny nie sú nakonfigurované"
          },
          "next-irrigation": {
            title: "Ďalšia závlaha",
            labels: {
              "next-start": "Ďalší štart",
              duration: "Trvanie",
              zones: "Zóny"
            },
            "no-data": "Žiadne dáta k dispozícii"
          },
          "irrigation-reason": {
            title: "Dôvod závlahy",
            labels: {
              reason: "Dôvod",
              sunrise: "Východ slnka",
              "total-duration": "Celková doba",
              explanation: "Vysvetlenie"
            },
            "no-data": "Žiadne dáta k dispozícii"
          },
          irrigate_now: {
            title: "Zavlažiť teraz",
            description: "Okamžite spustiť závlahu pre všetky zóny s prepojenou entitou. Podmienky preskočenia sú ignorované.",
            button_all: "Spustiť všetky zóny teraz",
            no_linked_zones: "Žiadna zóna nemá prepojenú entitu prepínača/ventilu s vypočítanou dobou."
          }
        }
      },
      setup: {
        title: "Nastavenie"
      }
    },
    $a = "Inteligentné zavlažovanie",
    Ra = {
      title: "Súradnice Polohy",
      description: "Nakonfigurujte súradnice polohy pre získavanie meteorologických údajov. Môžete použiť manuálne súradnice odlišné od vašej polohy Home Assistant ak je to potrebné.",
      manual_enabled: "Použiť manuálne súradnice",
      use_ha_location: "Použiť polohu Home Assistant",
      latitude: "Zemepisná šírka (desatinné stupne)",
      longitude: "Zemepisná dĺžka (desatinné stupne)",
      elevation: "Nadmorská výška (metre nad morom)",
      current_ha_coords: "Aktuálne súradnice Home Assistant"
    },
    Va = {
      title: "Dni medzi závlahami",
      description: "Nakonfigurujte minimálny počet dní medzi záhradnými udalosťami.",
      label: "Minimálne dni medzi závlahami",
      help_text: "Nastavte na 0 pre deaktiváciu. Podporované sú hodnoty 1-365 dní."
    },
    Ua = {
      title: "Spúšťače spustenia zavlažovania",
      description: "Nakonfiguruj, kedy sa má spustiť zavlažovanie na základe slnečných udalostí. Môžeš pridať viacero spúšťačov pre rôzne harmonogramy. Pri spúšťačoch východu slnka sa pri posune 0 automaticky použije celkové trvanie všetkých povolených zón.",
      add_trigger: "Pridať spúšťač",
      edit_trigger: "Upraviť spúšťač",
      delete_trigger: "Odstrániť spúšťač",
      trigger_types: {
        sunrise: "Východ slnka",
        sunset: "Západ slnka",
        solar_azimuth: "Slnečný azimut"
      },
      fields: {
        name: {
          name: "Názov spúšťača",
          description: "Popisný názov na identifikáciu tohto spúšťača"
        },
        type: {
          name: "Typ spúšťača",
          description: "Typ slnečnej udalosti, na ktorú sa má spustiť"
        },
        enabled: {
          name: "Povolené",
          description: "Či je tento spúšťač momentálne aktívny"
        },
        offset_minutes: {
          name: "Posun (minúty)",
          description: "Minúty pred (-) alebo po (+) slnečnej udalosti. Pri spúšťačoch východu slnka použi 0 pre automatické načasovanie na základe celkového trvania zón."
        },
        azimuth_angle: {
          name: "Uhol azimutu (stupne)",
          description: "Uhol slnečného azimutu v stupňoch, kde 0=sever, 90=východ, 180=juh, 270=západ"
        },
        account_for_duration: {
          name: "Zohľadniť trvanie",
          description: "Ak je povolené, zavlažovanie sa spustí dostatočne skoro, aby skončilo v zadanom čase. Ak je zakázané, zavlažovanie sa spustí presne v zadanom čase."
        }
      },
      dialog: {
        add_title: "Pridať spúšťač spustenia zavlažovania",
        edit_title: "Upraviť spúšťač spustenia zavlažovania",
        cancel: "Zrušiť",
        save: "Uložiť",
        delete: "Odstrániť"
      },
      no_triggers: "Nie sú nakonfigurované žiadne spúšťače spustenia zavlažovania. Systém použije predvolené správanie (východ slnka s celkovým trvaním zón). Pridaj spúšťače na prispôsobenie spustenia zavlažovania.",
      offset_auto: "Automaticky (vypočítané z celkového trvania zón)",
      confirm_delete: "Naozaj chceš odstrániť spúšťač '{name}'?",
      validation: {
        name_required: "Názov spúšťača je povinný",
        azimuth_invalid: "Uhol azimutu musí byť platné číslo"
      },
      help: {
        sunrise_offset: "Pri spúšťačoch východu slnka: použi záporné hodnoty na spustenie pred východom slnka, kladné na spustenie po ňom. Nastav na 0 na automatické spustenie dostatočne skoro, aby sa všetky zóny dokončili pred východom slnka.",
        sunset_offset: "Pri spúšťačoch západu slnka: použi záporné hodnoty na spustenie pred západom slnka, kladné na spustenie po západe slnka.",
        azimuth_explanation: "Slnečný azimut je kompasový smer slnka. 0°=sever, 90°=východ, 180°=juh, 270°=západ. Môžeš zadať ľubovoľnú hodnotu uhla (napr. 450° = 90°, -30° = 330°). Použi to na spustenie zavlažovania, keď slnko dosiahne konkrétnu polohu.",
        multiple_triggers: "Môžeš nakonfigurovať viacero spúšťačov. Každý povolený spúšťač naplánuje spustenie zavlažovania nezávisle."
      }
    },
    qa = {
      title: "Podmienky preskočenia",
      description: "Automaticky preskočiť závlahu pri nepriaznivých podmienkach. Kontroly zrážok, teploty a vetra vyžadujú počasiovú službu.",
      threshold_label: "Prah zrážok",
      threshold_description: "Minimálne celkové predpokladané zrážky (v mm) v okne predpovede na preskočenie závlahy.",
      lookahead_label: "Okno predpovede (dni)",
      lookahead_help: "Koľko nasledujúcich dní predpovede sa spočíta pri kontrole dažďa. Predpoveď začína zajtrajškom (dnešok je vylúčený), takže 1 = iba nasledujúci deň, 2 = nasledujúce dva dni atď.",
      temp_section_title: "Preskočiť pri nízkej teplote",
      temp_threshold_label: "Preskočiť ak teplota pod",
      wind_section_title: "Preskočiť pri silnom vetre",
      wind_threshold_label: "Preskočiť ak rýchlosť vetra nad",
      rain_sensor_section_title: "Podmienka dažďového senzora",
      rain_sensor_label: "Entita dažďového senzora (voliteľné)",
      rain_sensor_placeholder: "napr. binary_sensor.dazd"
    },
    Za = {
      title: "Poradie zón",
      description: "Keď viacero zón potrebuje závlahu, vyberte, či prebiehajú súčasne alebo jedna po druhej. V sekvenčnom režime systém čaká, kým každá zóna skončí, pred spustením ďalšej.",
      parallel: "Paralelne (všetky zóny súčasne)",
      sequential: "Sekvenčne (jedna zóna naraz)",
      rotating: "Rotujúce (zóny sa striedajú)",
      max_consecutive_duration_label: "Max. súvislý čas behu na zónu",
      max_consecutive_duration_unit: "minúty",
      min_absorption_time_label: "Min. čas vsiaknutia medzi cyklami",
      min_absorption_time_unit: "minúty (0 = vypnuté)"
    },
    Fa = {
      title: "Poveternostná služba",
      description: "Nakonfiguruj, ktorá poveternostná služba sa použije na výpočty ET a podmienky preskočenia.",
      enabled_label: "Povoliť poveternostnú službu",
      service_label: "Poveternostná služba",
      api_key_label: "API kľúč",
      api_key_placeholder: "Nechaj prázdne na zachovanie existujúceho kľúča",
      api_key_configured: "API kľúč je nakonfigurovaný",
      api_key_not_configured: "Nie je nakonfigurovaný žiadny API kľúč",
      api_key_help: "API kľúč od tebou zvoleného poskytovateľa poveternostnej služby. Open-Meteo nevyžaduje kľúč. OpenWeatherMap aj Pirate Weather ponúkajú bezplatné úrovne.",
      no_api_key_needed: "Open-Meteo je bezplatná služba a nevyžaduje API kľúč.",
      save_button: "Uložiť nastavenia počasia",
      saved: "Nastavenia počasia uložené",
      openmeteo: "Open-Meteo (zdarma, bez kľúča)",
      test_button: "Otestovať pripojenie",
      test_button_testing: "Testuje sa…",
      test_success: "✓ Pripojenie úspešné",
      test_error_invalid_auth: "✗ Neplatný API kľúč — skontroluj, či je správny a aktívny",
      test_error_cannot_connect: "✗ Nedá sa pripojiť — skontroluj svoje internetové pripojenie",
      test_error_no_service: "✗ Najprv vyber poveternostnú službu",
      test_error_unknown: "✗ Test zlyhal — neznáma chyba",
      owm: "OpenWeatherMap",
      pw: "Pirate Weather"
    },
    Wa = {
      zone_size: "Celková zavlažovaná plocha tejto zóny. Používa sa spolu s prietokom na výpočet množstva vody aplikovaného počas jedného cyklu.",
      zone_throughput: "Celkový prietok vody tvojho zavlažovacieho systému pre túto zónu (litre/min v metrickej sústave, gal/min v imperiálnej). Skontroluj technický list svojich postrekovačov alebo zmeraj, ako dlho trvá naplnenie nádoby známeho objemu.",
      zone_drainage_rate: "Ako rýchlo prebytočná voda odteká z pôdy, keď je vedro plné. Typicky: trávnik 50 mm/h, piesočnatá pôda 100+ mm/h, íl 10 mm/h.",
      zone_bucket: "Aktuálny deficit (záporný) alebo prebytok (kladný) vody pre túto zónu. Zavlažovanie sa spustí, keď vedro klesne pod prahovú hodnotu.",
      zone_maximum_bucket: "Maximálny prebytok vlhkosti, ktorý zóna dokáže zadržať. Voda nad touto úrovňou sa považuje za odtok. Typická hodnota: 50 mm.",
      zone_bucket_threshold: "Zavlažovanie sa spustí, keď vedro klesne pod túto hodnotu. Musí byť 0 alebo záporná. 0 znamená zavlažovať vždy, keď je deficit.",
      zone_multiplier: "Mierka aplikovaná na vypočítané trvanie. Nad 1,0 zvyšuje, pod 1,0 znižuje. Užitočné na jemné doladenie bez zmeny fyzických meraní.",
      zone_lead_time: "Sekundy navyše pred spustením zavlažovania. Použi to na zahriatie čerpadla alebo natlakovanie systému.",
      zone_maximum_duration: "Pevný horný limit pre jeden zavlažovací cyklus v sekundách. Zabraňuje nekontrolovanému zavlažovaniu. Predvolené: 3600 s (1 hodina).",
      zone_linked_entity: "Entita prepínača alebo ventilu v HA, ktorá riadi prietok vody pre túto zónu. Táto entita sa zapne, keď beží zavlažovanie.",
      zone_flow_sensor: "Voliteľný senzor merajúci skutočný prietok vody. Používa sa len na vykazovanie — neovplyvňuje výpočet trvania.",
      general_autoupdatedelay: "Sekundy čakania po spustení HA pred prvým získaním poveternostných údajov. Umožňuje ostatným integráciám sa najprv inicializovať.",
      general_sensor_debounce: "Minimálny odstup v milisekundách medzi načítaniami senzora na odfiltrovanie šumu z rýchlo sa meniacich senzorov.",
      general_calctime: "Čas dňa, kedy sa trvania zavlažovania prepočítajú zo získaných poveternostných údajov. Formát: HH:MM (24-hodinový).",
      general_cleardatatime: "Čas dňa, kedy sa odstránia staré poveternostné údaje. Musí byť nastavený neskôr ako čas výpočtu.",
      general_days_between: "Minimálny počet dní medzi zavlažovaniami tej istej zóny. Nastav na 0 na vypnutie (zavlažovať vždy, keď je deficit).",
      general_autoupdateinterval: "Ako často sa získavajú poveternostné údaje. Zvoľ hodnotu, ktorá vyvažuje čerstvé údaje a limity API.",
      general_precipitation_threshold: "Zavlažovanie sa preskočí, ak celkové predpovedané zrážky v okne predpovede prekročia toto množstvo.",
      general_temp_threshold: "Zavlažovanie sa preskočí, ak je aktuálna teplota pod touto hodnotou (napr. na zabránenie poškodeniu mrazom).",
      general_wind_threshold: "Zavlažovanie sa preskočí, ak rýchlosť vetra prekročí túto hodnotu (silný vietor znižuje účinnosť a spôsobuje úlet)."
    },
    Ga = {
      title: "Sprievodca nastavením",
      open_button: "Sprievodca nastavením",
      close: "Zavrieť",
      next: "Ďalej",
      back: "Späť",
      finish: "Dokončiť",
      skip_step: "Preskočiť tento krok",
      step_indicator: "Krok {current} z {total}",
      setup_complete_banner: "Nastavenie nie je dokončené. Spusti sprievodcu a začni.",
      open_wizard: "Otvoriť sprievodcu",
      steps: {
        welcome: {
          title: "Vitaj v Smart Irrigation",
          intro: "Tento sprievodca ťa prevedie štyrmi krokmi potrebnými na to, aby tvoja prvá zóna automaticky zavlažovala.",
          step1_label: "Poveternostná služba — odkiaľ získať poveternostné údaje",
          step2_label: "Výpočtový modul — ako sa počíta trvanie zavlažovania",
          step3_label: "Skupina senzorov — ktoré zdroje údajov použiť",
          step4_label: "Zóna — tvoja prvá zavlažovacia zóna",
          tip: "Ktorýkoľvek krok môžeš preskočiť a nakonfigurovať ho neskôr na karte Nastavenie."
        },
        weather: {
          title: "Poveternostná služba",
          description: "Vyber, ako sa získavajú poveternostné údaje. Open-Meteo je zadarmo a nevyžaduje API kľúč — pre väčšinu používateľov najjednoduchšia voľba."
        },
        module: {
          title: "Výpočtový modul",
          description: "Modul vypočíta, ako dlho zavlažovať, na základe evapotranspirácie (ET). Modul PyETO (metóda FAO-56) sa odporúča pre väčšinu používateľov.",
          pick_label: "Vyber typ modulu",
          no_modules: "Nie sú dostupné žiadne typy modulov."
        },
        mapping: {
          title: "Skupina senzorov",
          description: "Skupina senzorov prepája každú poveternostnú premennú s dátovým zdrojom. Nastav kľúčové premenné nižšie — jednotlivé priradenia senzorov môžeš spresniť neskôr na karte Nastavenie → Skupiny senzorov.",
          name_label: "Názov skupiny senzorov",
          source_label: "Zdroj údajov pre",
          use_weather_service: "Poveternostná služba",
          use_sensor: "Senzor",
          use_static: "Statická hodnota",
          use_none: "Žiadny / nepoužité"
        },
        zone: {
          title: "Prvá zóna",
          description: "Zóna je jedna zavlažovaná plocha (napr. trávnik, záhon). Nastav fyzické vlastnosti, aby systém mohol vypočítať správne trvanie zavlažovania.",
          name_label: "Názov zóny",
          size_label: "Plocha",
          throughput_label: "Prietok postrekovača",
          entity_label: "Prepojený prepínač alebo ventil",
          entity_placeholder: "napr. switch.garden_valve",
          module_label: "Výpočtový modul",
          mapping_label: "Skupina senzorov"
        },
        done: {
          title: "Nastavenie dokončené!",
          description: "Tvoja prvá zóna je pripravená. Smart Irrigation teraz bude automaticky počítať trvania zavlažovania na základe poveternostných údajov.",
          next_steps: "Čo môžeš urobiť ďalej:",
          tip1: "Prejdi na Zóny a zobraz vypočítané trvania a hodnoty vedra.",
          tip2: "Pridaj ďalšie zóny na karte Zóny.",
          tip3: "Doladi všetky nastavenia na karte Nastavenie.",
          go_zones: "Prejsť na Zóny",
          go_setup: "Prejsť na Nastavenie"
        }
      },
      stepper: {
        weather: "Počasie",
        module: "Modul",
        mapping: "Skupina senzorov",
        zone: "Zóna"
      },
      confirm_close: {
        body: "Zavrieť sprievodcu nastavením? Váš doterajší postup je uložený.",
        keep: "Pokračovať",
        close: "Zavrieť"
      }
    },
    Ka = {
      common: La,
      defaults: Ba,
      module: Na,
      calcmodules: Ia,
      panels: Oa,
      title: $a,
      coordinate_config: Ra,
      days_between_irrigation: Va,
      irrigation_start_triggers: Ua,
      weather_skip: qa,
      zone_sequencing: Za,
      weather_service_config: Fa,
      field_help: Wa,
      wizard: Ga
    },
    Xa = Object.freeze({
      __proto__: null,
      common: La,
      defaults: Ba,
      module: Na,
      calcmodules: Ia,
      panels: Oa,
      title: $a,
      coordinate_config: Ra,
      days_between_irrigation: Va,
      irrigation_start_triggers: Ua,
      weather_skip: qa,
      zone_sequencing: Za,
      weather_service_config: Fa,
      field_help: Wa,
      wizard: Ga,
      default: Ka
    });
  function Ya(e, t) {
    var a = t && t.cache ? t.cache : si,
      i = t && t.serializer ? t.serializer : ai;
    return (t && t.strategy ? t.strategy : ti)(e, {
      cache: a,
      serializer: i
    });
  }
  function Ja(e, t, a, i) {
    var n,
      r = null == (n = i) || "number" == typeof n || "boolean" == typeof n ? i : a(i),
      o = t.get(r);
    return void 0 === o && (o = e.call(this, i), t.set(r, o)), o;
  }
  function Qa(e, t, a) {
    var i = Array.prototype.slice.call(arguments, 3),
      n = a(i),
      r = t.get(n);
    return void 0 === r && (r = e.apply(this, i), t.set(n, r)), r;
  }
  function ei(e, t, a, i, n) {
    return a.bind(t, e, i, n);
  }
  function ti(e, t) {
    return ei(e, this, 1 === e.length ? Ja : Qa, t.cache.create(), t.serializer);
  }
  var ai = function () {
    return JSON.stringify(arguments);
  };
  function ii() {
    this.cache = Object.create(null);
  }
  ii.prototype.get = function (e) {
    return this.cache[e];
  }, ii.prototype.set = function (e, t) {
    this.cache[e] = t;
  };
  var ni,
    ri,
    oi,
    si = {
      create: function () {
        return new ii();
      }
    },
    li = {
      variadic: function (e, t) {
        return ei(e, this, Qa, t.cache.create(), t.serializer);
      },
      monadic: function (e, t) {
        return ei(e, this, Ja, t.cache.create(), t.serializer);
      }
    };
  function di(e) {
    return e.type === ri.literal;
  }
  function ui(e) {
    return e.type === ri.argument;
  }
  function ci(e) {
    return e.type === ri.number;
  }
  function pi(e) {
    return e.type === ri.date;
  }
  function mi(e) {
    return e.type === ri.time;
  }
  function gi(e) {
    return e.type === ri.select;
  }
  function hi(e) {
    return e.type === ri.plural;
  }
  function vi(e) {
    return e.type === ri.pound;
  }
  function _i(e) {
    return e.type === ri.tag;
  }
  function bi(e) {
    return !(!e || "object" != typeof e || e.type !== oi.number);
  }
  function fi(e) {
    return !(!e || "object" != typeof e || e.type !== oi.dateTime);
  }
  !function (e) {
    e[e.EXPECT_ARGUMENT_CLOSING_BRACE = 1] = "EXPECT_ARGUMENT_CLOSING_BRACE", e[e.EMPTY_ARGUMENT = 2] = "EMPTY_ARGUMENT", e[e.MALFORMED_ARGUMENT = 3] = "MALFORMED_ARGUMENT", e[e.EXPECT_ARGUMENT_TYPE = 4] = "EXPECT_ARGUMENT_TYPE", e[e.INVALID_ARGUMENT_TYPE = 5] = "INVALID_ARGUMENT_TYPE", e[e.EXPECT_ARGUMENT_STYLE = 6] = "EXPECT_ARGUMENT_STYLE", e[e.INVALID_NUMBER_SKELETON = 7] = "INVALID_NUMBER_SKELETON", e[e.INVALID_DATE_TIME_SKELETON = 8] = "INVALID_DATE_TIME_SKELETON", e[e.EXPECT_NUMBER_SKELETON = 9] = "EXPECT_NUMBER_SKELETON", e[e.EXPECT_DATE_TIME_SKELETON = 10] = "EXPECT_DATE_TIME_SKELETON", e[e.UNCLOSED_QUOTE_IN_ARGUMENT_STYLE = 11] = "UNCLOSED_QUOTE_IN_ARGUMENT_STYLE", e[e.EXPECT_SELECT_ARGUMENT_OPTIONS = 12] = "EXPECT_SELECT_ARGUMENT_OPTIONS", e[e.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE = 13] = "EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE", e[e.INVALID_PLURAL_ARGUMENT_OFFSET_VALUE = 14] = "INVALID_PLURAL_ARGUMENT_OFFSET_VALUE", e[e.EXPECT_SELECT_ARGUMENT_SELECTOR = 15] = "EXPECT_SELECT_ARGUMENT_SELECTOR", e[e.EXPECT_PLURAL_ARGUMENT_SELECTOR = 16] = "EXPECT_PLURAL_ARGUMENT_SELECTOR", e[e.EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT = 17] = "EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT", e[e.EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT = 18] = "EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT", e[e.INVALID_PLURAL_ARGUMENT_SELECTOR = 19] = "INVALID_PLURAL_ARGUMENT_SELECTOR", e[e.DUPLICATE_PLURAL_ARGUMENT_SELECTOR = 20] = "DUPLICATE_PLURAL_ARGUMENT_SELECTOR", e[e.DUPLICATE_SELECT_ARGUMENT_SELECTOR = 21] = "DUPLICATE_SELECT_ARGUMENT_SELECTOR", e[e.MISSING_OTHER_CLAUSE = 22] = "MISSING_OTHER_CLAUSE", e[e.INVALID_TAG = 23] = "INVALID_TAG", e[e.INVALID_TAG_NAME = 25] = "INVALID_TAG_NAME", e[e.UNMATCHED_CLOSING_TAG = 26] = "UNMATCHED_CLOSING_TAG", e[e.UNCLOSED_TAG = 27] = "UNCLOSED_TAG";
  }(ni || (ni = {})), function (e) {
    e[e.literal = 0] = "literal", e[e.argument = 1] = "argument", e[e.number = 2] = "number", e[e.date = 3] = "date", e[e.time = 4] = "time", e[e.select = 5] = "select", e[e.plural = 6] = "plural", e[e.pound = 7] = "pound", e[e.tag = 8] = "tag";
  }(ri || (ri = {})), function (e) {
    e[e.number = 0] = "number", e[e.dateTime = 1] = "dateTime";
  }(oi || (oi = {}));
  var ki = /[ \xA0\u1680\u2000-\u200A\u202F\u205F\u3000]/,
    zi = /(?:[Eec]{1,6}|G{1,5}|[Qq]{1,5}|(?:[yYur]+|U{1,5})|[ML]{1,5}|d{1,2}|D{1,3}|F{1}|[abB]{1,5}|[hkHK]{1,2}|w{1,2}|W{1}|m{1,2}|s{1,2}|[zZOvVxX]{1,4})(?=([^']*'[^']*')*[^']*$)/g;
  function yi(e) {
    var t = {};
    return e.replace(zi, function (e) {
      var a = e.length;
      switch (e[0]) {
        case "G":
          t.era = 4 === a ? "long" : 5 === a ? "narrow" : "short";
          break;
        case "y":
          t.year = 2 === a ? "2-digit" : "numeric";
          break;
        case "Y":
        case "u":
        case "U":
        case "r":
          throw new RangeError("`Y/u/U/r` (year) patterns are not supported, use `y` instead");
        case "q":
        case "Q":
          throw new RangeError("`q/Q` (quarter) patterns are not supported");
        case "M":
        case "L":
          t.month = ["numeric", "2-digit", "short", "long", "narrow"][a - 1];
          break;
        case "w":
        case "W":
          throw new RangeError("`w/W` (week) patterns are not supported");
        case "d":
          t.day = ["numeric", "2-digit"][a - 1];
          break;
        case "D":
        case "F":
        case "g":
          throw new RangeError("`D/F/g` (day) patterns are not supported, use `d` instead");
        case "E":
          t.weekday = 4 === a ? "long" : 5 === a ? "narrow" : "short";
          break;
        case "e":
          if (a < 4) throw new RangeError("`e..eee` (weekday) patterns are not supported");
          t.weekday = ["short", "long", "narrow", "short"][a - 4];
          break;
        case "c":
          if (a < 4) throw new RangeError("`c..ccc` (weekday) patterns are not supported");
          t.weekday = ["short", "long", "narrow", "short"][a - 4];
          break;
        case "a":
          t.hour12 = !0;
          break;
        case "b":
        case "B":
          throw new RangeError("`b/B` (period) patterns are not supported, use `a` instead");
        case "h":
          t.hourCycle = "h12", t.hour = ["numeric", "2-digit"][a - 1];
          break;
        case "H":
          t.hourCycle = "h23", t.hour = ["numeric", "2-digit"][a - 1];
          break;
        case "K":
          t.hourCycle = "h11", t.hour = ["numeric", "2-digit"][a - 1];
          break;
        case "k":
          t.hourCycle = "h24", t.hour = ["numeric", "2-digit"][a - 1];
          break;
        case "j":
        case "J":
        case "C":
          throw new RangeError("`j/J/C` (hour) patterns are not supported, use `h/H/K/k` instead");
        case "m":
          t.minute = ["numeric", "2-digit"][a - 1];
          break;
        case "s":
          t.second = ["numeric", "2-digit"][a - 1];
          break;
        case "S":
        case "A":
          throw new RangeError("`S/A` (second) patterns are not supported, use `s` instead");
        case "z":
          t.timeZoneName = a < 4 ? "short" : "long";
          break;
        case "Z":
        case "O":
        case "v":
        case "V":
        case "X":
        case "x":
          throw new RangeError("`Z/O/v/V/X/x` (timeZone) patterns are not supported, use `z` instead");
      }
      return "";
    }), t;
  }
  var wi = /[\t-\r \x85\u200E\u200F\u2028\u2029]/i;
  var Ai = /^\.(?:(0+)(\*)?|(#+)|(0+)(#+))$/g,
    Si = /^(@+)?(\+|#+)?[rs]?$/g,
    Ei = /(\*)(0+)|(#+)(0+)|(0+)/g,
    xi = /^(0+)$/;
  function Ti(e) {
    var t = {};
    return "r" === e[e.length - 1] ? t.roundingPriority = "morePrecision" : "s" === e[e.length - 1] && (t.roundingPriority = "lessPrecision"), e.replace(Si, function (e, a, i) {
      return "string" != typeof i ? (t.minimumSignificantDigits = a.length, t.maximumSignificantDigits = a.length) : "+" === i ? t.minimumSignificantDigits = a.length : "#" === a[0] ? t.maximumSignificantDigits = a.length : (t.minimumSignificantDigits = a.length, t.maximumSignificantDigits = a.length + ("string" == typeof i ? i.length : 0)), "";
    }), t;
  }
  function ji(e) {
    switch (e) {
      case "sign-auto":
        return {
          signDisplay: "auto"
        };
      case "sign-accounting":
      case "()":
        return {
          currencySign: "accounting"
        };
      case "sign-always":
      case "+!":
        return {
          signDisplay: "always"
        };
      case "sign-accounting-always":
      case "()!":
        return {
          signDisplay: "always",
          currencySign: "accounting"
        };
      case "sign-except-zero":
      case "+?":
        return {
          signDisplay: "exceptZero"
        };
      case "sign-accounting-except-zero":
      case "()?":
        return {
          signDisplay: "exceptZero",
          currencySign: "accounting"
        };
      case "sign-never":
      case "+_":
        return {
          signDisplay: "never"
        };
    }
  }
  function Pi(e) {
    var t;
    if ("E" === e[0] && "E" === e[1] ? (t = {
      notation: "engineering"
    }, e = e.slice(2)) : "E" === e[0] && (t = {
      notation: "scientific"
    }, e = e.slice(1)), t) {
      var a = e.slice(0, 2);
      if ("+!" === a ? (t.signDisplay = "always", e = e.slice(2)) : "+?" === a && (t.signDisplay = "exceptZero", e = e.slice(2)), !xi.test(e)) throw new Error("Malformed concise eng/scientific notation");
      t.minimumIntegerDigits = e.length;
    }
    return t;
  }
  function Mi(e) {
    var t = ji(e);
    return t || {};
  }
  function Di(e) {
    for (var t = {}, a = 0, n = e; a < n.length; a++) {
      var r = n[a];
      switch (r.stem) {
        case "percent":
        case "%":
          t.style = "percent";
          continue;
        case "%x100":
          t.style = "percent", t.scale = 100;
          continue;
        case "currency":
          t.style = "currency", t.currency = r.options[0];
          continue;
        case "group-off":
        case ",_":
          t.useGrouping = !1;
          continue;
        case "precision-integer":
        case ".":
          t.maximumFractionDigits = 0;
          continue;
        case "measure-unit":
        case "unit":
          t.style = "unit", t.unit = r.options[0].replace(/^(.*?)-/, "");
          continue;
        case "compact-short":
        case "K":
          t.notation = "compact", t.compactDisplay = "short";
          continue;
        case "compact-long":
        case "KK":
          t.notation = "compact", t.compactDisplay = "long";
          continue;
        case "scientific":
          t = i(i(i({}, t), {
            notation: "scientific"
          }), r.options.reduce(function (e, t) {
            return i(i({}, e), Mi(t));
          }, {}));
          continue;
        case "engineering":
          t = i(i(i({}, t), {
            notation: "engineering"
          }), r.options.reduce(function (e, t) {
            return i(i({}, e), Mi(t));
          }, {}));
          continue;
        case "notation-simple":
          t.notation = "standard";
          continue;
        case "unit-width-narrow":
          t.currencyDisplay = "narrowSymbol", t.unitDisplay = "narrow";
          continue;
        case "unit-width-short":
          t.currencyDisplay = "code", t.unitDisplay = "short";
          continue;
        case "unit-width-full-name":
          t.currencyDisplay = "name", t.unitDisplay = "long";
          continue;
        case "unit-width-iso-code":
          t.currencyDisplay = "symbol";
          continue;
        case "scale":
          t.scale = parseFloat(r.options[0]);
          continue;
        case "rounding-mode-floor":
          t.roundingMode = "floor";
          continue;
        case "rounding-mode-ceiling":
          t.roundingMode = "ceil";
          continue;
        case "rounding-mode-down":
          t.roundingMode = "trunc";
          continue;
        case "rounding-mode-up":
          t.roundingMode = "expand";
          continue;
        case "rounding-mode-half-even":
          t.roundingMode = "halfEven";
          continue;
        case "rounding-mode-half-down":
          t.roundingMode = "halfTrunc";
          continue;
        case "rounding-mode-half-up":
          t.roundingMode = "halfExpand";
          continue;
        case "integer-width":
          if (r.options.length > 1) throw new RangeError("integer-width stems only accept a single optional option");
          r.options[0].replace(Ei, function (e, a, i, n, r, o) {
            if (a) t.minimumIntegerDigits = i.length;else {
              if (n && r) throw new Error("We currently do not support maximum integer digits");
              if (o) throw new Error("We currently do not support exact integer digits");
            }
            return "";
          });
          continue;
      }
      if (xi.test(r.stem)) t.minimumIntegerDigits = r.stem.length;else if (Ai.test(r.stem)) {
        if (r.options.length > 1) throw new RangeError("Fraction-precision stems only accept a single optional option");
        r.stem.replace(Ai, function (e, a, i, n, r, o) {
          return "*" === i ? t.minimumFractionDigits = a.length : n && "#" === n[0] ? t.maximumFractionDigits = n.length : r && o ? (t.minimumFractionDigits = r.length, t.maximumFractionDigits = r.length + o.length) : (t.minimumFractionDigits = a.length, t.maximumFractionDigits = a.length), "";
        });
        var o = r.options[0];
        "w" === o ? t = i(i({}, t), {
          trailingZeroDisplay: "stripIfInteger"
        }) : o && (t = i(i({}, t), Ti(o)));
      } else if (Si.test(r.stem)) t = i(i({}, t), Ti(r.stem));else {
        var s = ji(r.stem);
        s && (t = i(i({}, t), s));
        var l = Pi(r.stem);
        l && (t = i(i({}, t), l));
      }
    }
    return t;
  }
  var Ci,
    Hi = {
      "001": ["H", "h"],
      419: ["h", "H", "hB", "hb"],
      AC: ["H", "h", "hb", "hB"],
      AD: ["H", "hB"],
      AE: ["h", "hB", "hb", "H"],
      AF: ["H", "hb", "hB", "h"],
      AG: ["h", "hb", "H", "hB"],
      AI: ["H", "h", "hb", "hB"],
      AL: ["h", "H", "hB"],
      AM: ["H", "hB"],
      AO: ["H", "hB"],
      AR: ["h", "H", "hB", "hb"],
      AS: ["h", "H"],
      AT: ["H", "hB"],
      AU: ["h", "hb", "H", "hB"],
      AW: ["H", "hB"],
      AX: ["H"],
      AZ: ["H", "hB", "h"],
      BA: ["H", "hB", "h"],
      BB: ["h", "hb", "H", "hB"],
      BD: ["h", "hB", "H"],
      BE: ["H", "hB"],
      BF: ["H", "hB"],
      BG: ["H", "hB", "h"],
      BH: ["h", "hB", "hb", "H"],
      BI: ["H", "h"],
      BJ: ["H", "hB"],
      BL: ["H", "hB"],
      BM: ["h", "hb", "H", "hB"],
      BN: ["hb", "hB", "h", "H"],
      BO: ["h", "H", "hB", "hb"],
      BQ: ["H"],
      BR: ["H", "hB"],
      BS: ["h", "hb", "H", "hB"],
      BT: ["h", "H"],
      BW: ["H", "h", "hb", "hB"],
      BY: ["H", "h"],
      BZ: ["H", "h", "hb", "hB"],
      CA: ["h", "hb", "H", "hB"],
      CC: ["H", "h", "hb", "hB"],
      CD: ["hB", "H"],
      CF: ["H", "h", "hB"],
      CG: ["H", "hB"],
      CH: ["H", "hB", "h"],
      CI: ["H", "hB"],
      CK: ["H", "h", "hb", "hB"],
      CL: ["h", "H", "hB", "hb"],
      CM: ["H", "h", "hB"],
      CN: ["H", "hB", "hb", "h"],
      CO: ["h", "H", "hB", "hb"],
      CP: ["H"],
      CR: ["h", "H", "hB", "hb"],
      CU: ["h", "H", "hB", "hb"],
      CV: ["H", "hB"],
      CW: ["H", "hB"],
      CX: ["H", "h", "hb", "hB"],
      CY: ["h", "H", "hb", "hB"],
      CZ: ["H"],
      DE: ["H", "hB"],
      DG: ["H", "h", "hb", "hB"],
      DJ: ["h", "H"],
      DK: ["H"],
      DM: ["h", "hb", "H", "hB"],
      DO: ["h", "H", "hB", "hb"],
      DZ: ["h", "hB", "hb", "H"],
      EA: ["H", "h", "hB", "hb"],
      EC: ["h", "H", "hB", "hb"],
      EE: ["H", "hB"],
      EG: ["h", "hB", "hb", "H"],
      EH: ["h", "hB", "hb", "H"],
      ER: ["h", "H"],
      ES: ["H", "hB", "h", "hb"],
      ET: ["hB", "hb", "h", "H"],
      FI: ["H"],
      FJ: ["h", "hb", "H", "hB"],
      FK: ["H", "h", "hb", "hB"],
      FM: ["h", "hb", "H", "hB"],
      FO: ["H", "h"],
      FR: ["H", "hB"],
      GA: ["H", "hB"],
      GB: ["H", "h", "hb", "hB"],
      GD: ["h", "hb", "H", "hB"],
      GE: ["H", "hB", "h"],
      GF: ["H", "hB"],
      GG: ["H", "h", "hb", "hB"],
      GH: ["h", "H"],
      GI: ["H", "h", "hb", "hB"],
      GL: ["H", "h"],
      GM: ["h", "hb", "H", "hB"],
      GN: ["H", "hB"],
      GP: ["H", "hB"],
      GQ: ["H", "hB", "h", "hb"],
      GR: ["h", "H", "hb", "hB"],
      GT: ["h", "H", "hB", "hb"],
      GU: ["h", "hb", "H", "hB"],
      GW: ["H", "hB"],
      GY: ["h", "hb", "H", "hB"],
      HK: ["h", "hB", "hb", "H"],
      HN: ["h", "H", "hB", "hb"],
      HR: ["H", "hB"],
      HU: ["H", "h"],
      IC: ["H", "h", "hB", "hb"],
      ID: ["H"],
      IE: ["H", "h", "hb", "hB"],
      IL: ["H", "hB"],
      IM: ["H", "h", "hb", "hB"],
      IN: ["h", "H"],
      IO: ["H", "h", "hb", "hB"],
      IQ: ["h", "hB", "hb", "H"],
      IR: ["hB", "H"],
      IS: ["H"],
      IT: ["H", "hB"],
      JE: ["H", "h", "hb", "hB"],
      JM: ["h", "hb", "H", "hB"],
      JO: ["h", "hB", "hb", "H"],
      JP: ["H", "K", "h"],
      KE: ["hB", "hb", "H", "h"],
      KG: ["H", "h", "hB", "hb"],
      KH: ["hB", "h", "H", "hb"],
      KI: ["h", "hb", "H", "hB"],
      KM: ["H", "h", "hB", "hb"],
      KN: ["h", "hb", "H", "hB"],
      KP: ["h", "H", "hB", "hb"],
      KR: ["h", "H", "hB", "hb"],
      KW: ["h", "hB", "hb", "H"],
      KY: ["h", "hb", "H", "hB"],
      KZ: ["H", "hB"],
      LA: ["H", "hb", "hB", "h"],
      LB: ["h", "hB", "hb", "H"],
      LC: ["h", "hb", "H", "hB"],
      LI: ["H", "hB", "h"],
      LK: ["H", "h", "hB", "hb"],
      LR: ["h", "hb", "H", "hB"],
      LS: ["h", "H"],
      LT: ["H", "h", "hb", "hB"],
      LU: ["H", "h", "hB"],
      LV: ["H", "hB", "hb", "h"],
      LY: ["h", "hB", "hb", "H"],
      MA: ["H", "h", "hB", "hb"],
      MC: ["H", "hB"],
      MD: ["H", "hB"],
      ME: ["H", "hB", "h"],
      MF: ["H", "hB"],
      MG: ["H", "h"],
      MH: ["h", "hb", "H", "hB"],
      MK: ["H", "h", "hb", "hB"],
      ML: ["H"],
      MM: ["hB", "hb", "H", "h"],
      MN: ["H", "h", "hb", "hB"],
      MO: ["h", "hB", "hb", "H"],
      MP: ["h", "hb", "H", "hB"],
      MQ: ["H", "hB"],
      MR: ["h", "hB", "hb", "H"],
      MS: ["H", "h", "hb", "hB"],
      MT: ["H", "h"],
      MU: ["H", "h"],
      MV: ["H", "h"],
      MW: ["h", "hb", "H", "hB"],
      MX: ["h", "H", "hB", "hb"],
      MY: ["hb", "hB", "h", "H"],
      MZ: ["H", "hB"],
      NA: ["h", "H", "hB", "hb"],
      NC: ["H", "hB"],
      NE: ["H"],
      NF: ["H", "h", "hb", "hB"],
      NG: ["H", "h", "hb", "hB"],
      NI: ["h", "H", "hB", "hb"],
      NL: ["H", "hB"],
      NO: ["H", "h"],
      NP: ["H", "h", "hB"],
      NR: ["H", "h", "hb", "hB"],
      NU: ["H", "h", "hb", "hB"],
      NZ: ["h", "hb", "H", "hB"],
      OM: ["h", "hB", "hb", "H"],
      PA: ["h", "H", "hB", "hb"],
      PE: ["h", "H", "hB", "hb"],
      PF: ["H", "h", "hB"],
      PG: ["h", "H"],
      PH: ["h", "hB", "hb", "H"],
      PK: ["h", "hB", "H"],
      PL: ["H", "h"],
      PM: ["H", "hB"],
      PN: ["H", "h", "hb", "hB"],
      PR: ["h", "H", "hB", "hb"],
      PS: ["h", "hB", "hb", "H"],
      PT: ["H", "hB"],
      PW: ["h", "H"],
      PY: ["h", "H", "hB", "hb"],
      QA: ["h", "hB", "hb", "H"],
      RE: ["H", "hB"],
      RO: ["H", "hB"],
      RS: ["H", "hB", "h"],
      RU: ["H"],
      RW: ["H", "h"],
      SA: ["h", "hB", "hb", "H"],
      SB: ["h", "hb", "H", "hB"],
      SC: ["H", "h", "hB"],
      SD: ["h", "hB", "hb", "H"],
      SE: ["H"],
      SG: ["h", "hb", "H", "hB"],
      SH: ["H", "h", "hb", "hB"],
      SI: ["H", "hB"],
      SJ: ["H"],
      SK: ["H"],
      SL: ["h", "hb", "H", "hB"],
      SM: ["H", "h", "hB"],
      SN: ["H", "h", "hB"],
      SO: ["h", "H"],
      SR: ["H", "hB"],
      SS: ["h", "hb", "H", "hB"],
      ST: ["H", "hB"],
      SV: ["h", "H", "hB", "hb"],
      SX: ["H", "h", "hb", "hB"],
      SY: ["h", "hB", "hb", "H"],
      SZ: ["h", "hb", "H", "hB"],
      TA: ["H", "h", "hb", "hB"],
      TC: ["h", "hb", "H", "hB"],
      TD: ["h", "H", "hB"],
      TF: ["H", "h", "hB"],
      TG: ["H", "hB"],
      TH: ["H", "h"],
      TJ: ["H", "h"],
      TL: ["H", "hB", "hb", "h"],
      TM: ["H", "h"],
      TN: ["h", "hB", "hb", "H"],
      TO: ["h", "H"],
      TR: ["H", "hB"],
      TT: ["h", "hb", "H", "hB"],
      TW: ["hB", "hb", "h", "H"],
      TZ: ["hB", "hb", "H", "h"],
      UA: ["H", "hB", "h"],
      UG: ["hB", "hb", "H", "h"],
      UM: ["h", "hb", "H", "hB"],
      US: ["h", "hb", "H", "hB"],
      UY: ["h", "H", "hB", "hb"],
      UZ: ["H", "hB", "h"],
      VA: ["H", "h", "hB"],
      VC: ["h", "hb", "H", "hB"],
      VE: ["h", "H", "hB", "hb"],
      VG: ["h", "hb", "H", "hB"],
      VI: ["h", "hb", "H", "hB"],
      VN: ["H", "h"],
      VU: ["h", "H"],
      WF: ["H", "hB"],
      WS: ["h", "H"],
      XK: ["H", "hB", "h"],
      YE: ["h", "hB", "hb", "H"],
      YT: ["H", "hB"],
      ZA: ["H", "h", "hb", "hB"],
      ZM: ["h", "hb", "H", "hB"],
      ZW: ["H", "h"],
      "af-ZA": ["H", "h", "hB", "hb"],
      "ar-001": ["h", "hB", "hb", "H"],
      "ca-ES": ["H", "h", "hB"],
      "en-001": ["h", "hb", "H", "hB"],
      "en-HK": ["h", "hb", "H", "hB"],
      "en-IL": ["H", "h", "hb", "hB"],
      "en-MY": ["h", "hb", "H", "hB"],
      "es-BR": ["H", "h", "hB", "hb"],
      "es-ES": ["H", "h", "hB", "hb"],
      "es-GQ": ["H", "h", "hB", "hb"],
      "fr-CA": ["H", "h", "hB"],
      "gl-ES": ["H", "h", "hB"],
      "gu-IN": ["hB", "hb", "h", "H"],
      "hi-IN": ["hB", "h", "H"],
      "it-CH": ["H", "h", "hB"],
      "it-IT": ["H", "h", "hB"],
      "kn-IN": ["hB", "h", "H"],
      "ml-IN": ["hB", "h", "H"],
      "mr-IN": ["hB", "hb", "h", "H"],
      "pa-IN": ["hB", "hb", "h", "H"],
      "ta-IN": ["hB", "h", "hb", "H"],
      "te-IN": ["hB", "h", "H"],
      "zu-ZA": ["H", "hB", "hb", "h"]
    };
  function Li(e) {
    var t = e.hourCycle;
    if (void 0 === t && e.hourCycles && e.hourCycles.length && (t = e.hourCycles[0]), t) switch (t) {
      case "h24":
        return "k";
      case "h23":
        return "H";
      case "h12":
        return "h";
      case "h11":
        return "K";
      default:
        throw new Error("Invalid hourCycle");
    }
    var a,
      i = e.language;
    return "root" !== i && (a = e.maximize().region), (Hi[a || ""] || Hi[i || ""] || Hi["".concat(i, "-001")] || Hi["001"])[0];
  }
  var Bi = new RegExp("^".concat(ki.source, "*")),
    Ni = new RegExp("".concat(ki.source, "*$"));
  function Ii(e, t) {
    return {
      start: e,
      end: t
    };
  }
  var Oi = !!String.prototype.startsWith && "_a".startsWith("a", 1),
    $i = !!String.fromCodePoint,
    Ri = !!Object.fromEntries,
    Vi = !!String.prototype.codePointAt,
    Ui = !!String.prototype.trimStart,
    qi = !!String.prototype.trimEnd,
    Zi = !!Number.isSafeInteger ? Number.isSafeInteger : function (e) {
      return "number" == typeof e && isFinite(e) && Math.floor(e) === e && Math.abs(e) <= 9007199254740991;
    },
    Fi = !0;
  try {
    Fi = "a" === (null === (Ci = en("([^\\p{White_Space}\\p{Pattern_Syntax}]*)", "yu").exec("a")) || void 0 === Ci ? void 0 : Ci[0]);
  } catch (N) {
    Fi = !1;
  }
  var Wi,
    Gi = Oi ? function (e, t, a) {
      return e.startsWith(t, a);
    } : function (e, t, a) {
      return e.slice(a, a + t.length) === t;
    },
    Ki = $i ? String.fromCodePoint : function () {
      for (var e = [], t = 0; t < arguments.length; t++) e[t] = arguments[t];
      for (var a, i = "", n = e.length, r = 0; n > r;) {
        if ((a = e[r++]) > 1114111) throw RangeError(a + " is not a valid code point");
        i += a < 65536 ? String.fromCharCode(a) : String.fromCharCode(55296 + ((a -= 65536) >> 10), a % 1024 + 56320);
      }
      return i;
    },
    Xi = Ri ? Object.fromEntries : function (e) {
      for (var t = {}, a = 0, i = e; a < i.length; a++) {
        var n = i[a],
          r = n[0],
          o = n[1];
        t[r] = o;
      }
      return t;
    },
    Yi = Vi ? function (e, t) {
      return e.codePointAt(t);
    } : function (e, t) {
      var a = e.length;
      if (!(t < 0 || t >= a)) {
        var i,
          n = e.charCodeAt(t);
        return n < 55296 || n > 56319 || t + 1 === a || (i = e.charCodeAt(t + 1)) < 56320 || i > 57343 ? n : i - 56320 + (n - 55296 << 10) + 65536;
      }
    },
    Ji = Ui ? function (e) {
      return e.trimStart();
    } : function (e) {
      return e.replace(Bi, "");
    },
    Qi = qi ? function (e) {
      return e.trimEnd();
    } : function (e) {
      return e.replace(Ni, "");
    };
  function en(e, t) {
    return new RegExp(e, t);
  }
  if (Fi) {
    var tn = en("([^\\p{White_Space}\\p{Pattern_Syntax}]*)", "yu");
    Wi = function (e, t) {
      var a;
      return tn.lastIndex = t, null !== (a = tn.exec(e)[1]) && void 0 !== a ? a : "";
    };
  } else Wi = function (e, t) {
    for (var a = [];;) {
      var i = Yi(e, t);
      if (void 0 === i || sn(i) || ln(i)) break;
      a.push(i), t += i >= 65536 ? 2 : 1;
    }
    return Ki.apply(void 0, a);
  };
  var an,
    nn = function () {
      function e(e, t) {
        void 0 === t && (t = {}), this.message = e, this.position = {
          offset: 0,
          line: 1,
          column: 1
        }, this.ignoreTag = !!t.ignoreTag, this.locale = t.locale, this.requiresOtherClause = !!t.requiresOtherClause, this.shouldParseSkeletons = !!t.shouldParseSkeletons;
      }
      return e.prototype.parse = function () {
        if (0 !== this.offset()) throw Error("parser can only be used once");
        return this.parseMessage(0, "", !1);
      }, e.prototype.parseMessage = function (e, t, a) {
        for (var i = []; !this.isEOF();) {
          var n = this.char();
          if (123 === n) {
            if ((r = this.parseArgument(e, a)).err) return r;
            i.push(r.val);
          } else {
            if (125 === n && e > 0) break;
            if (35 !== n || "plural" !== t && "selectordinal" !== t) {
              if (60 === n && !this.ignoreTag && 47 === this.peek()) {
                if (a) break;
                return this.error(ni.UNMATCHED_CLOSING_TAG, Ii(this.clonePosition(), this.clonePosition()));
              }
              if (60 === n && !this.ignoreTag && rn(this.peek() || 0)) {
                if ((r = this.parseTag(e, t)).err) return r;
                i.push(r.val);
              } else {
                var r;
                if ((r = this.parseLiteral(e, t)).err) return r;
                i.push(r.val);
              }
            } else {
              var o = this.clonePosition();
              this.bump(), i.push({
                type: ri.pound,
                location: Ii(o, this.clonePosition())
              });
            }
          }
        }
        return {
          val: i,
          err: null
        };
      }, e.prototype.parseTag = function (e, t) {
        var a = this.clonePosition();
        this.bump();
        var i = this.parseTagName();
        if (this.bumpSpace(), this.bumpIf("/>")) return {
          val: {
            type: ri.literal,
            value: "<".concat(i, "/>"),
            location: Ii(a, this.clonePosition())
          },
          err: null
        };
        if (this.bumpIf(">")) {
          var n = this.parseMessage(e + 1, t, !0);
          if (n.err) return n;
          var r = n.val,
            o = this.clonePosition();
          if (this.bumpIf("</")) {
            if (this.isEOF() || !rn(this.char())) return this.error(ni.INVALID_TAG, Ii(o, this.clonePosition()));
            var s = this.clonePosition();
            return i !== this.parseTagName() ? this.error(ni.UNMATCHED_CLOSING_TAG, Ii(s, this.clonePosition())) : (this.bumpSpace(), this.bumpIf(">") ? {
              val: {
                type: ri.tag,
                value: i,
                children: r,
                location: Ii(a, this.clonePosition())
              },
              err: null
            } : this.error(ni.INVALID_TAG, Ii(o, this.clonePosition())));
          }
          return this.error(ni.UNCLOSED_TAG, Ii(a, this.clonePosition()));
        }
        return this.error(ni.INVALID_TAG, Ii(a, this.clonePosition()));
      }, e.prototype.parseTagName = function () {
        var e = this.offset();
        for (this.bump(); !this.isEOF() && on(this.char());) this.bump();
        return this.message.slice(e, this.offset());
      }, e.prototype.parseLiteral = function (e, t) {
        for (var a = this.clonePosition(), i = "";;) {
          var n = this.tryParseQuote(t);
          if (n) i += n;else {
            var r = this.tryParseUnquoted(e, t);
            if (r) i += r;else {
              var o = this.tryParseLeftAngleBracket();
              if (!o) break;
              i += o;
            }
          }
        }
        var s = Ii(a, this.clonePosition());
        return {
          val: {
            type: ri.literal,
            value: i,
            location: s
          },
          err: null
        };
      }, e.prototype.tryParseLeftAngleBracket = function () {
        return this.isEOF() || 60 !== this.char() || !this.ignoreTag && (rn(e = this.peek() || 0) || 47 === e) ? null : (this.bump(), "<");
        var e;
      }, e.prototype.tryParseQuote = function (e) {
        if (this.isEOF() || 39 !== this.char()) return null;
        switch (this.peek()) {
          case 39:
            return this.bump(), this.bump(), "'";
          case 123:
          case 60:
          case 62:
          case 125:
            break;
          case 35:
            if ("plural" === e || "selectordinal" === e) break;
            return null;
          default:
            return null;
        }
        this.bump();
        var t = [this.char()];
        for (this.bump(); !this.isEOF();) {
          var a = this.char();
          if (39 === a) {
            if (39 !== this.peek()) {
              this.bump();
              break;
            }
            t.push(39), this.bump();
          } else t.push(a);
          this.bump();
        }
        return Ki.apply(void 0, t);
      }, e.prototype.tryParseUnquoted = function (e, t) {
        if (this.isEOF()) return null;
        var a = this.char();
        return 60 === a || 123 === a || 35 === a && ("plural" === t || "selectordinal" === t) || 125 === a && e > 0 ? null : (this.bump(), Ki(a));
      }, e.prototype.parseArgument = function (e, t) {
        var a = this.clonePosition();
        if (this.bump(), this.bumpSpace(), this.isEOF()) return this.error(ni.EXPECT_ARGUMENT_CLOSING_BRACE, Ii(a, this.clonePosition()));
        if (125 === this.char()) return this.bump(), this.error(ni.EMPTY_ARGUMENT, Ii(a, this.clonePosition()));
        var i = this.parseIdentifierIfPossible().value;
        if (!i) return this.error(ni.MALFORMED_ARGUMENT, Ii(a, this.clonePosition()));
        if (this.bumpSpace(), this.isEOF()) return this.error(ni.EXPECT_ARGUMENT_CLOSING_BRACE, Ii(a, this.clonePosition()));
        switch (this.char()) {
          case 125:
            return this.bump(), {
              val: {
                type: ri.argument,
                value: i,
                location: Ii(a, this.clonePosition())
              },
              err: null
            };
          case 44:
            return this.bump(), this.bumpSpace(), this.isEOF() ? this.error(ni.EXPECT_ARGUMENT_CLOSING_BRACE, Ii(a, this.clonePosition())) : this.parseArgumentOptions(e, t, i, a);
          default:
            return this.error(ni.MALFORMED_ARGUMENT, Ii(a, this.clonePosition()));
        }
      }, e.prototype.parseIdentifierIfPossible = function () {
        var e = this.clonePosition(),
          t = this.offset(),
          a = Wi(this.message, t),
          i = t + a.length;
        return this.bumpTo(i), {
          value: a,
          location: Ii(e, this.clonePosition())
        };
      }, e.prototype.parseArgumentOptions = function (e, t, a, n) {
        var r,
          o = this.clonePosition(),
          s = this.parseIdentifierIfPossible().value,
          l = this.clonePosition();
        switch (s) {
          case "":
            return this.error(ni.EXPECT_ARGUMENT_TYPE, Ii(o, l));
          case "number":
          case "date":
          case "time":
            this.bumpSpace();
            var d = null;
            if (this.bumpIf(",")) {
              this.bumpSpace();
              var u = this.clonePosition();
              if ((b = this.parseSimpleArgStyleIfPossible()).err) return b;
              if (0 === (g = Qi(b.val)).length) return this.error(ni.EXPECT_ARGUMENT_STYLE, Ii(this.clonePosition(), this.clonePosition()));
              d = {
                style: g,
                styleLocation: Ii(u, this.clonePosition())
              };
            }
            if ((f = this.tryParseArgumentClose(n)).err) return f;
            var c = Ii(n, this.clonePosition());
            if (d && Gi(null == d ? void 0 : d.style, "::", 0)) {
              var p = Ji(d.style.slice(2));
              if ("number" === s) return (b = this.parseNumberSkeletonFromString(p, d.styleLocation)).err ? b : {
                val: {
                  type: ri.number,
                  value: a,
                  location: c,
                  style: b.val
                },
                err: null
              };
              if (0 === p.length) return this.error(ni.EXPECT_DATE_TIME_SKELETON, c);
              var m = p;
              this.locale && (m = function (e, t) {
                for (var a = "", i = 0; i < e.length; i++) {
                  var n = e.charAt(i);
                  if ("j" === n) {
                    for (var r = 0; i + 1 < e.length && e.charAt(i + 1) === n;) r++, i++;
                    var o = 1 + (1 & r),
                      s = r < 2 ? 1 : 3 + (r >> 1),
                      l = Li(t);
                    for ("H" != l && "k" != l || (s = 0); s-- > 0;) a += "a";
                    for (; o-- > 0;) a = l + a;
                  } else a += "J" === n ? "H" : n;
                }
                return a;
              }(p, this.locale));
              var g = {
                type: oi.dateTime,
                pattern: m,
                location: d.styleLocation,
                parsedOptions: this.shouldParseSkeletons ? yi(m) : {}
              };
              return {
                val: {
                  type: "date" === s ? ri.date : ri.time,
                  value: a,
                  location: c,
                  style: g
                },
                err: null
              };
            }
            return {
              val: {
                type: "number" === s ? ri.number : "date" === s ? ri.date : ri.time,
                value: a,
                location: c,
                style: null !== (r = null == d ? void 0 : d.style) && void 0 !== r ? r : null
              },
              err: null
            };
          case "plural":
          case "selectordinal":
          case "select":
            var h = this.clonePosition();
            if (this.bumpSpace(), !this.bumpIf(",")) return this.error(ni.EXPECT_SELECT_ARGUMENT_OPTIONS, Ii(h, i({}, h)));
            this.bumpSpace();
            var v = this.parseIdentifierIfPossible(),
              _ = 0;
            if ("select" !== s && "offset" === v.value) {
              if (!this.bumpIf(":")) return this.error(ni.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE, Ii(this.clonePosition(), this.clonePosition()));
              var b;
              if (this.bumpSpace(), (b = this.tryParseDecimalInteger(ni.EXPECT_PLURAL_ARGUMENT_OFFSET_VALUE, ni.INVALID_PLURAL_ARGUMENT_OFFSET_VALUE)).err) return b;
              this.bumpSpace(), v = this.parseIdentifierIfPossible(), _ = b.val;
            }
            var f,
              k = this.tryParsePluralOrSelectOptions(e, s, t, v);
            if (k.err) return k;
            if ((f = this.tryParseArgumentClose(n)).err) return f;
            var z = Ii(n, this.clonePosition());
            return "select" === s ? {
              val: {
                type: ri.select,
                value: a,
                options: Xi(k.val),
                location: z
              },
              err: null
            } : {
              val: {
                type: ri.plural,
                value: a,
                options: Xi(k.val),
                offset: _,
                pluralType: "plural" === s ? "cardinal" : "ordinal",
                location: z
              },
              err: null
            };
          default:
            return this.error(ni.INVALID_ARGUMENT_TYPE, Ii(o, l));
        }
      }, e.prototype.tryParseArgumentClose = function (e) {
        return this.isEOF() || 125 !== this.char() ? this.error(ni.EXPECT_ARGUMENT_CLOSING_BRACE, Ii(e, this.clonePosition())) : (this.bump(), {
          val: !0,
          err: null
        });
      }, e.prototype.parseSimpleArgStyleIfPossible = function () {
        for (var e = 0, t = this.clonePosition(); !this.isEOF();) {
          switch (this.char()) {
            case 39:
              this.bump();
              var a = this.clonePosition();
              if (!this.bumpUntil("'")) return this.error(ni.UNCLOSED_QUOTE_IN_ARGUMENT_STYLE, Ii(a, this.clonePosition()));
              this.bump();
              break;
            case 123:
              e += 1, this.bump();
              break;
            case 125:
              if (!(e > 0)) return {
                val: this.message.slice(t.offset, this.offset()),
                err: null
              };
              e -= 1;
              break;
            default:
              this.bump();
          }
        }
        return {
          val: this.message.slice(t.offset, this.offset()),
          err: null
        };
      }, e.prototype.parseNumberSkeletonFromString = function (e, t) {
        var a = [];
        try {
          a = function (e) {
            if (0 === e.length) throw new Error("Number skeleton cannot be empty");
            for (var t = e.split(wi).filter(function (e) {
                return e.length > 0;
              }), a = [], i = 0, n = t; i < n.length; i++) {
              var r = n[i].split("/");
              if (0 === r.length) throw new Error("Invalid number skeleton");
              for (var o = r[0], s = r.slice(1), l = 0, d = s; l < d.length; l++) if (0 === d[l].length) throw new Error("Invalid number skeleton");
              a.push({
                stem: o,
                options: s
              });
            }
            return a;
          }(e);
        } catch (e) {
          return this.error(ni.INVALID_NUMBER_SKELETON, t);
        }
        return {
          val: {
            type: oi.number,
            tokens: a,
            location: t,
            parsedOptions: this.shouldParseSkeletons ? Di(a) : {}
          },
          err: null
        };
      }, e.prototype.tryParsePluralOrSelectOptions = function (e, t, a, i) {
        for (var n, r = !1, o = [], s = new Set(), l = i.value, d = i.location;;) {
          if (0 === l.length) {
            var u = this.clonePosition();
            if ("select" === t || !this.bumpIf("=")) break;
            var c = this.tryParseDecimalInteger(ni.EXPECT_PLURAL_ARGUMENT_SELECTOR, ni.INVALID_PLURAL_ARGUMENT_SELECTOR);
            if (c.err) return c;
            d = Ii(u, this.clonePosition()), l = this.message.slice(u.offset, this.offset());
          }
          if (s.has(l)) return this.error("select" === t ? ni.DUPLICATE_SELECT_ARGUMENT_SELECTOR : ni.DUPLICATE_PLURAL_ARGUMENT_SELECTOR, d);
          "other" === l && (r = !0), this.bumpSpace();
          var p = this.clonePosition();
          if (!this.bumpIf("{")) return this.error("select" === t ? ni.EXPECT_SELECT_ARGUMENT_SELECTOR_FRAGMENT : ni.EXPECT_PLURAL_ARGUMENT_SELECTOR_FRAGMENT, Ii(this.clonePosition(), this.clonePosition()));
          var m = this.parseMessage(e + 1, t, a);
          if (m.err) return m;
          var g = this.tryParseArgumentClose(p);
          if (g.err) return g;
          o.push([l, {
            value: m.val,
            location: Ii(p, this.clonePosition())
          }]), s.add(l), this.bumpSpace(), l = (n = this.parseIdentifierIfPossible()).value, d = n.location;
        }
        return 0 === o.length ? this.error("select" === t ? ni.EXPECT_SELECT_ARGUMENT_SELECTOR : ni.EXPECT_PLURAL_ARGUMENT_SELECTOR, Ii(this.clonePosition(), this.clonePosition())) : this.requiresOtherClause && !r ? this.error(ni.MISSING_OTHER_CLAUSE, Ii(this.clonePosition(), this.clonePosition())) : {
          val: o,
          err: null
        };
      }, e.prototype.tryParseDecimalInteger = function (e, t) {
        var a = 1,
          i = this.clonePosition();
        this.bumpIf("+") || this.bumpIf("-") && (a = -1);
        for (var n = !1, r = 0; !this.isEOF();) {
          var o = this.char();
          if (!(o >= 48 && o <= 57)) break;
          n = !0, r = 10 * r + (o - 48), this.bump();
        }
        var s = Ii(i, this.clonePosition());
        return n ? Zi(r *= a) ? {
          val: r,
          err: null
        } : this.error(t, s) : this.error(e, s);
      }, e.prototype.offset = function () {
        return this.position.offset;
      }, e.prototype.isEOF = function () {
        return this.offset() === this.message.length;
      }, e.prototype.clonePosition = function () {
        return {
          offset: this.position.offset,
          line: this.position.line,
          column: this.position.column
        };
      }, e.prototype.char = function () {
        var e = this.position.offset;
        if (e >= this.message.length) throw Error("out of bound");
        var t = Yi(this.message, e);
        if (void 0 === t) throw Error("Offset ".concat(e, " is at invalid UTF-16 code unit boundary"));
        return t;
      }, e.prototype.error = function (e, t) {
        return {
          val: null,
          err: {
            kind: e,
            message: this.message,
            location: t
          }
        };
      }, e.prototype.bump = function () {
        if (!this.isEOF()) {
          var e = this.char();
          10 === e ? (this.position.line += 1, this.position.column = 1, this.position.offset += 1) : (this.position.column += 1, this.position.offset += e < 65536 ? 1 : 2);
        }
      }, e.prototype.bumpIf = function (e) {
        if (Gi(this.message, e, this.offset())) {
          for (var t = 0; t < e.length; t++) this.bump();
          return !0;
        }
        return !1;
      }, e.prototype.bumpUntil = function (e) {
        var t = this.offset(),
          a = this.message.indexOf(e, t);
        return a >= 0 ? (this.bumpTo(a), !0) : (this.bumpTo(this.message.length), !1);
      }, e.prototype.bumpTo = function (e) {
        if (this.offset() > e) throw Error("targetOffset ".concat(e, " must be greater than or equal to the current offset ").concat(this.offset()));
        for (e = Math.min(e, this.message.length);;) {
          var t = this.offset();
          if (t === e) break;
          if (t > e) throw Error("targetOffset ".concat(e, " is at invalid UTF-16 code unit boundary"));
          if (this.bump(), this.isEOF()) break;
        }
      }, e.prototype.bumpSpace = function () {
        for (; !this.isEOF() && sn(this.char());) this.bump();
      }, e.prototype.peek = function () {
        if (this.isEOF()) return null;
        var e = this.char(),
          t = this.offset(),
          a = this.message.charCodeAt(t + (e >= 65536 ? 2 : 1));
        return null != a ? a : null;
      }, e;
    }();
  function rn(e) {
    return e >= 97 && e <= 122 || e >= 65 && e <= 90;
  }
  function on(e) {
    return 45 === e || 46 === e || e >= 48 && e <= 57 || 95 === e || e >= 97 && e <= 122 || e >= 65 && e <= 90 || 183 == e || e >= 192 && e <= 214 || e >= 216 && e <= 246 || e >= 248 && e <= 893 || e >= 895 && e <= 8191 || e >= 8204 && e <= 8205 || e >= 8255 && e <= 8256 || e >= 8304 && e <= 8591 || e >= 11264 && e <= 12271 || e >= 12289 && e <= 55295 || e >= 63744 && e <= 64975 || e >= 65008 && e <= 65533 || e >= 65536 && e <= 983039;
  }
  function sn(e) {
    return e >= 9 && e <= 13 || 32 === e || 133 === e || e >= 8206 && e <= 8207 || 8232 === e || 8233 === e;
  }
  function ln(e) {
    return e >= 33 && e <= 35 || 36 === e || e >= 37 && e <= 39 || 40 === e || 41 === e || 42 === e || 43 === e || 44 === e || 45 === e || e >= 46 && e <= 47 || e >= 58 && e <= 59 || e >= 60 && e <= 62 || e >= 63 && e <= 64 || 91 === e || 92 === e || 93 === e || 94 === e || 96 === e || 123 === e || 124 === e || 125 === e || 126 === e || 161 === e || e >= 162 && e <= 165 || 166 === e || 167 === e || 169 === e || 171 === e || 172 === e || 174 === e || 176 === e || 177 === e || 182 === e || 187 === e || 191 === e || 215 === e || 247 === e || e >= 8208 && e <= 8213 || e >= 8214 && e <= 8215 || 8216 === e || 8217 === e || 8218 === e || e >= 8219 && e <= 8220 || 8221 === e || 8222 === e || 8223 === e || e >= 8224 && e <= 8231 || e >= 8240 && e <= 8248 || 8249 === e || 8250 === e || e >= 8251 && e <= 8254 || e >= 8257 && e <= 8259 || 8260 === e || 8261 === e || 8262 === e || e >= 8263 && e <= 8273 || 8274 === e || 8275 === e || e >= 8277 && e <= 8286 || e >= 8592 && e <= 8596 || e >= 8597 && e <= 8601 || e >= 8602 && e <= 8603 || e >= 8604 && e <= 8607 || 8608 === e || e >= 8609 && e <= 8610 || 8611 === e || e >= 8612 && e <= 8613 || 8614 === e || e >= 8615 && e <= 8621 || 8622 === e || e >= 8623 && e <= 8653 || e >= 8654 && e <= 8655 || e >= 8656 && e <= 8657 || 8658 === e || 8659 === e || 8660 === e || e >= 8661 && e <= 8691 || e >= 8692 && e <= 8959 || e >= 8960 && e <= 8967 || 8968 === e || 8969 === e || 8970 === e || 8971 === e || e >= 8972 && e <= 8991 || e >= 8992 && e <= 8993 || e >= 8994 && e <= 9e3 || 9001 === e || 9002 === e || e >= 9003 && e <= 9083 || 9084 === e || e >= 9085 && e <= 9114 || e >= 9115 && e <= 9139 || e >= 9140 && e <= 9179 || e >= 9180 && e <= 9185 || e >= 9186 && e <= 9254 || e >= 9255 && e <= 9279 || e >= 9280 && e <= 9290 || e >= 9291 && e <= 9311 || e >= 9472 && e <= 9654 || 9655 === e || e >= 9656 && e <= 9664 || 9665 === e || e >= 9666 && e <= 9719 || e >= 9720 && e <= 9727 || e >= 9728 && e <= 9838 || 9839 === e || e >= 9840 && e <= 10087 || 10088 === e || 10089 === e || 10090 === e || 10091 === e || 10092 === e || 10093 === e || 10094 === e || 10095 === e || 10096 === e || 10097 === e || 10098 === e || 10099 === e || 10100 === e || 10101 === e || e >= 10132 && e <= 10175 || e >= 10176 && e <= 10180 || 10181 === e || 10182 === e || e >= 10183 && e <= 10213 || 10214 === e || 10215 === e || 10216 === e || 10217 === e || 10218 === e || 10219 === e || 10220 === e || 10221 === e || 10222 === e || 10223 === e || e >= 10224 && e <= 10239 || e >= 10240 && e <= 10495 || e >= 10496 && e <= 10626 || 10627 === e || 10628 === e || 10629 === e || 10630 === e || 10631 === e || 10632 === e || 10633 === e || 10634 === e || 10635 === e || 10636 === e || 10637 === e || 10638 === e || 10639 === e || 10640 === e || 10641 === e || 10642 === e || 10643 === e || 10644 === e || 10645 === e || 10646 === e || 10647 === e || 10648 === e || e >= 10649 && e <= 10711 || 10712 === e || 10713 === e || 10714 === e || 10715 === e || e >= 10716 && e <= 10747 || 10748 === e || 10749 === e || e >= 10750 && e <= 11007 || e >= 11008 && e <= 11055 || e >= 11056 && e <= 11076 || e >= 11077 && e <= 11078 || e >= 11079 && e <= 11084 || e >= 11085 && e <= 11123 || e >= 11124 && e <= 11125 || e >= 11126 && e <= 11157 || 11158 === e || e >= 11159 && e <= 11263 || e >= 11776 && e <= 11777 || 11778 === e || 11779 === e || 11780 === e || 11781 === e || e >= 11782 && e <= 11784 || 11785 === e || 11786 === e || 11787 === e || 11788 === e || 11789 === e || e >= 11790 && e <= 11798 || 11799 === e || e >= 11800 && e <= 11801 || 11802 === e || 11803 === e || 11804 === e || 11805 === e || e >= 11806 && e <= 11807 || 11808 === e || 11809 === e || 11810 === e || 11811 === e || 11812 === e || 11813 === e || 11814 === e || 11815 === e || 11816 === e || 11817 === e || e >= 11818 && e <= 11822 || 11823 === e || e >= 11824 && e <= 11833 || e >= 11834 && e <= 11835 || e >= 11836 && e <= 11839 || 11840 === e || 11841 === e || 11842 === e || e >= 11843 && e <= 11855 || e >= 11856 && e <= 11857 || 11858 === e || e >= 11859 && e <= 11903 || e >= 12289 && e <= 12291 || 12296 === e || 12297 === e || 12298 === e || 12299 === e || 12300 === e || 12301 === e || 12302 === e || 12303 === e || 12304 === e || 12305 === e || e >= 12306 && e <= 12307 || 12308 === e || 12309 === e || 12310 === e || 12311 === e || 12312 === e || 12313 === e || 12314 === e || 12315 === e || 12316 === e || 12317 === e || e >= 12318 && e <= 12319 || 12320 === e || 12336 === e || 64830 === e || 64831 === e || e >= 65093 && e <= 65094;
  }
  function dn(e) {
    e.forEach(function (e) {
      if (delete e.location, gi(e) || hi(e)) for (var t in e.options) delete e.options[t].location, dn(e.options[t].value);else ci(e) && bi(e.style) || (pi(e) || mi(e)) && fi(e.style) ? delete e.style.location : _i(e) && dn(e.children);
    });
  }
  function un(e, t) {
    void 0 === t && (t = {}), t = i({
      shouldParseSkeletons: !0,
      requiresOtherClause: !0
    }, t);
    var a = new nn(e, t).parse();
    if (a.err) {
      var n = SyntaxError(ni[a.err.kind]);
      throw n.location = a.err.location, n.originalMessage = a.err.message, n;
    }
    return (null == t ? void 0 : t.captureLocation) || dn(a.val), a.val;
  }
  !function (e) {
    e.MISSING_VALUE = "MISSING_VALUE", e.INVALID_VALUE = "INVALID_VALUE", e.MISSING_INTL_API = "MISSING_INTL_API";
  }(an || (an = {}));
  var cn,
    pn = function (e) {
      function t(t, a, i) {
        var n = e.call(this, t) || this;
        return n.code = a, n.originalMessage = i, n;
      }
      return a(t, e), t.prototype.toString = function () {
        return "[formatjs Error: ".concat(this.code, "] ").concat(this.message);
      }, t;
    }(Error),
    mn = function (e) {
      function t(t, a, i, n) {
        return e.call(this, 'Invalid values for "'.concat(t, '": "').concat(a, '". Options are "').concat(Object.keys(i).join('", "'), '"'), an.INVALID_VALUE, n) || this;
      }
      return a(t, e), t;
    }(pn),
    gn = function (e) {
      function t(t, a, i) {
        return e.call(this, 'Value for "'.concat(t, '" must be of type ').concat(a), an.INVALID_VALUE, i) || this;
      }
      return a(t, e), t;
    }(pn),
    hn = function (e) {
      function t(t, a) {
        return e.call(this, 'The intl string context variable "'.concat(t, '" was not provided to the string "').concat(a, '"'), an.MISSING_VALUE, a) || this;
      }
      return a(t, e), t;
    }(pn);
  function vn(e) {
    return "function" == typeof e;
  }
  function _n(e, t, a, i, n, r, o) {
    if (1 === e.length && di(e[0])) return [{
      type: cn.literal,
      value: e[0].value
    }];
    for (var s = [], l = 0, d = e; l < d.length; l++) {
      var u = d[l];
      if (di(u)) s.push({
        type: cn.literal,
        value: u.value
      });else if (vi(u)) "number" == typeof r && s.push({
        type: cn.literal,
        value: a.getNumberFormat(t).format(r)
      });else {
        var c = u.value;
        if (!n || !(c in n)) throw new hn(c, o);
        var p = n[c];
        if (ui(u)) p && "string" != typeof p && "number" != typeof p || (p = "string" == typeof p || "number" == typeof p ? String(p) : ""), s.push({
          type: "string" == typeof p ? cn.literal : cn.object,
          value: p
        });else if (pi(u)) {
          var m = "string" == typeof u.style ? i.date[u.style] : fi(u.style) ? u.style.parsedOptions : void 0;
          s.push({
            type: cn.literal,
            value: a.getDateTimeFormat(t, m).format(p)
          });
        } else if (mi(u)) {
          m = "string" == typeof u.style ? i.time[u.style] : fi(u.style) ? u.style.parsedOptions : i.time.medium;
          s.push({
            type: cn.literal,
            value: a.getDateTimeFormat(t, m).format(p)
          });
        } else if (ci(u)) {
          (m = "string" == typeof u.style ? i.number[u.style] : bi(u.style) ? u.style.parsedOptions : void 0) && m.scale && (p *= m.scale || 1), s.push({
            type: cn.literal,
            value: a.getNumberFormat(t, m).format(p)
          });
        } else {
          if (_i(u)) {
            var g = u.children,
              h = u.value,
              v = n[h];
            if (!vn(v)) throw new gn(h, "function", o);
            var _ = v(_n(g, t, a, i, n, r).map(function (e) {
              return e.value;
            }));
            Array.isArray(_) || (_ = [_]), s.push.apply(s, _.map(function (e) {
              return {
                type: "string" == typeof e ? cn.literal : cn.object,
                value: e
              };
            }));
          }
          if (gi(u)) {
            if (!(b = u.options[p] || u.options.other)) throw new mn(u.value, p, Object.keys(u.options), o);
            s.push.apply(s, _n(b.value, t, a, i, n));
          } else if (hi(u)) {
            var b;
            if (!(b = u.options["=".concat(p)])) {
              if (!Intl.PluralRules) throw new pn('Intl.PluralRules is not available in this environment.\nTry polyfilling it using "@formatjs/intl-pluralrules"\n', an.MISSING_INTL_API, o);
              var f = a.getPluralRules(t, {
                type: u.pluralType
              }).select(p - (u.offset || 0));
              b = u.options[f] || u.options.other;
            }
            if (!b) throw new mn(u.value, p, Object.keys(u.options), o);
            s.push.apply(s, _n(b.value, t, a, i, n, p - (u.offset || 0)));
          } else ;
        }
      }
    }
    return function (e) {
      return e.length < 2 ? e : e.reduce(function (e, t) {
        var a = e[e.length - 1];
        return a && a.type === cn.literal && t.type === cn.literal ? a.value += t.value : e.push(t), e;
      }, []);
    }(s);
  }
  function bn(e, t) {
    return t ? Object.keys(e).reduce(function (a, n) {
      var r, o;
      return a[n] = (r = e[n], (o = t[n]) ? i(i(i({}, r || {}), o || {}), Object.keys(r).reduce(function (e, t) {
        return e[t] = i(i({}, r[t]), o[t] || {}), e;
      }, {})) : r), a;
    }, i({}, e)) : e;
  }
  function fn(e) {
    return {
      create: function () {
        return {
          get: function (t) {
            return e[t];
          },
          set: function (t, a) {
            e[t] = a;
          }
        };
      }
    };
  }
  !function (e) {
    e[e.literal = 0] = "literal", e[e.object = 1] = "object";
  }(cn || (cn = {}));
  var kn = function () {
      function e(t, a, n, o) {
        void 0 === a && (a = e.defaultLocale);
        var s,
          l = this;
        if (this.formatterCache = {
          number: {},
          dateTime: {},
          pluralRules: {}
        }, this.format = function (e) {
          var t = l.formatToParts(e);
          if (1 === t.length) return t[0].value;
          var a = t.reduce(function (e, t) {
            return e.length && t.type === cn.literal && "string" == typeof e[e.length - 1] ? e[e.length - 1] += t.value : e.push(t.value), e;
          }, []);
          return a.length <= 1 ? a[0] || "" : a;
        }, this.formatToParts = function (e) {
          return _n(l.ast, l.locales, l.formatters, l.formats, e, void 0, l.message);
        }, this.resolvedOptions = function () {
          var e;
          return {
            locale: (null === (e = l.resolvedLocale) || void 0 === e ? void 0 : e.toString()) || Intl.NumberFormat.supportedLocalesOf(l.locales)[0]
          };
        }, this.getAst = function () {
          return l.ast;
        }, this.locales = a, this.resolvedLocale = e.resolveLocale(a), "string" == typeof t) {
          if (this.message = t, !e.__parse) throw new TypeError("IntlMessageFormat.__parse must be set to process `message` of type `string`");
          var d = o || {};
          d.formatters;
          var u = function (e, t) {
            var a = {};
            for (var i in e) Object.prototype.hasOwnProperty.call(e, i) && t.indexOf(i) < 0 && (a[i] = e[i]);
            if (null != e && "function" == typeof Object.getOwnPropertySymbols) {
              var n = 0;
              for (i = Object.getOwnPropertySymbols(e); n < i.length; n++) t.indexOf(i[n]) < 0 && Object.prototype.propertyIsEnumerable.call(e, i[n]) && (a[i[n]] = e[i[n]]);
            }
            return a;
          }(d, ["formatters"]);
          this.ast = e.__parse(t, i(i({}, u), {
            locale: this.resolvedLocale
          }));
        } else this.ast = t;
        if (!Array.isArray(this.ast)) throw new TypeError("A message must be provided as a String or AST.");
        this.formats = bn(e.formats, n), this.formatters = o && o.formatters || (void 0 === (s = this.formatterCache) && (s = {
          number: {},
          dateTime: {},
          pluralRules: {}
        }), {
          getNumberFormat: Ya(function () {
            for (var e, t = [], a = 0; a < arguments.length; a++) t[a] = arguments[a];
            return new ((e = Intl.NumberFormat).bind.apply(e, r([void 0], t, !1)))();
          }, {
            cache: fn(s.number),
            strategy: li.variadic
          }),
          getDateTimeFormat: Ya(function () {
            for (var e, t = [], a = 0; a < arguments.length; a++) t[a] = arguments[a];
            return new ((e = Intl.DateTimeFormat).bind.apply(e, r([void 0], t, !1)))();
          }, {
            cache: fn(s.dateTime),
            strategy: li.variadic
          }),
          getPluralRules: Ya(function () {
            for (var e, t = [], a = 0; a < arguments.length; a++) t[a] = arguments[a];
            return new ((e = Intl.PluralRules).bind.apply(e, r([void 0], t, !1)))();
          }, {
            cache: fn(s.pluralRules),
            strategy: li.variadic
          })
        });
      }
      return Object.defineProperty(e, "defaultLocale", {
        get: function () {
          return e.memoizedDefaultLocale || (e.memoizedDefaultLocale = new Intl.NumberFormat().resolvedOptions().locale), e.memoizedDefaultLocale;
        },
        enumerable: !1,
        configurable: !0
      }), e.memoizedDefaultLocale = null, e.resolveLocale = function (e) {
        if (void 0 !== Intl.Locale) {
          var t = Intl.NumberFormat.supportedLocalesOf(e);
          return t.length > 0 ? new Intl.Locale(t[0]) : new Intl.Locale("string" == typeof e ? e : e[0]);
        }
      }, e.__parse = un, e.formats = {
        number: {
          integer: {
            maximumFractionDigits: 0
          },
          currency: {
            style: "currency"
          },
          percent: {
            style: "percent"
          }
        },
        date: {
          short: {
            month: "numeric",
            day: "numeric",
            year: "2-digit"
          },
          medium: {
            month: "short",
            day: "numeric",
            year: "numeric"
          },
          long: {
            month: "long",
            day: "numeric",
            year: "numeric"
          },
          full: {
            weekday: "long",
            month: "long",
            day: "numeric",
            year: "numeric"
          }
        },
        time: {
          short: {
            hour: "numeric",
            minute: "numeric"
          },
          medium: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric"
          },
          long: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            timeZoneName: "short"
          },
          full: {
            hour: "numeric",
            minute: "numeric",
            second: "numeric",
            timeZoneName: "short"
          }
        }
      }, e;
    }(),
    zn = kn;
  const yn = {
    de: Fe,
    en: lt,
    es: At,
    fr: $t,
    it: aa,
    nl: ba,
    no: Ha,
    sk: Xa
  };
  function wn(e, t, ...a) {
    const i = t.replace(/['"]+/g, "");
    let n;
    try {
      n = e.split(".").reduce((e, t) => e[t], yn[i]);
    } catch (t) {
      n = e.split(".").reduce((e, t) => e[t], yn.en);
    }
    if (void 0 === n && (n = e.split(".").reduce((e, t) => e[t], yn.en)), !a.length) return n;
    const r = {};
    for (let e = 0; e < a.length; e += 2) {
      let t = a[e];
      t = t.replace(/^{([^}]+)?}$/, "$1"), r[t] = a[e + 1];
    }
    try {
      return new zn(n, t).format(r);
    } catch (e) {
      return "Translation " + e;
    }
  }
  function An(e, t) {
    switch (t) {
      case "drainage_rate":
        return e.units == ke ? U`${Pe("mm/h")}` : U`${Pe("in/h")}`;
      case "precipitation_threshold_mm":
      case ze:
        return e.units == ke ? U`${Pe("mm")}` : U`${Pe("in")}`;
      case "size":
        return e.units == ke ? U`${Pe("m<sup>2</sup>")}` : U`${Pe("sq ft")}`;
      case "throughput":
        return e.units == ke ? U`${Pe("l/minute")}` : U`${Pe("gal/minute")}`;
      default:
        return U``;
    }
  }
  const Sn = (e, t, a = !1) => {
    var i, n, r;
    a ? history.replaceState(null, "", t) : history.pushState(null, "", t), i = window, n = "location-changed", r = {
      replace: a
    }, i.dispatchEvent(new CustomEvent(n, {
      detail: r,
      bubbles: !0,
      composed: !0,
      cancelable: !1
    }));
  };
  function En(e) {
    var t;
    if (!e) return "Unknown error";
    if ("string" == typeof e) return e;
    const a = e;
    return (null === (t = null == a ? void 0 : a.body) || void 0 === t ? void 0 : t.message) || (null == a ? void 0 : a.message) || (null == a ? void 0 : a.error) || JSON.stringify(e);
  }
  function xn(e, t) {
    e.dispatchEvent(new CustomEvent("hass-notification", {
      detail: {
        message: t
      },
      bubbles: !0,
      composed: !0
    }));
  }
  function Tn(e, t, a, i) {
    var n;
    xn(e, `${wn(a, null !== (n = null == t ? void 0 : t.language) && void 0 !== n ? n : "en")}: ${En(i)}`);
  }
  const jn = (e, ...t) => {
      let a = {
        page: e,
        params: {}
      };
      t.forEach(e => {
        "string" == typeof e ? a = Object.assign(Object.assign({}, a), {
          subpage: e
        }) : "params" in e ? a = Object.assign(Object.assign({}, a), {
          params: e.params
        }) : "filter" in e && (a = Object.assign(Object.assign({}, a), {
          filter: e.filter
        }));
      });
      const i = e => {
        let t = Object.keys(e);
        t = t.filter(t => e[t]), t.sort();
        let a = "";
        return t.forEach(t => {
          const i = e[t];
          a = a.length ? `${a}/${t}/${i}` : `${t}/${i}`;
        }), a;
      };
      let n = `/${fe}/${a.page}`;
      return a.subpage && (n = `${n}/${a.subpage}`), i(a.params).length && (n = `${n}/${i(a.params)}`), a.filter && (n = `${n}/filter/${i(a.filter)}`), n;
    },
    Pn = c`
  /* Existing common styles */
  ha-card {
    display: flex;
    flex-direction: column;
    margin: 5px;
    max-width: calc(100vw - 10px);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
  }
  .card-header .name {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  span.dialog-header {
    font-size: 24px;
    letter-spacing: -0.012em;
    line-height: 48px;
    padding: 12px 16px 16px;
    display: block;
    margin-block: 0px;
    font-weight: 400;
  }

  div.warning {
    color: var(--error-color);
    margin-top: 20px;
  }

  div.checkbox-row {
    min-height: 40px;
    display: flex;
    align-items: center;
  }

  div.checkbox-row ha-switch {
    margin-right: 20px;
  }

  div.checkbox-row.right ha-switch {
    margin-left: 20px;
    position: absolute;
    right: 0px;
  }

  div.entity-row {
    display: flex;
    align-items: center;
    flex-direction: row;
    margin: 10px 0px;
  }
  div.entity-row .info {
    margin-left: 16px;
    flex: 1 0 60px;
  }
  div.entity-row .info,
  div.entity-row .info > * {
    color: var(--primary-text-color);
    transition: color 0.2s ease-in-out;
  }
  div.entity-row .secondary {
    display: block;
    color: var(--secondary-text-color);
    transition: color 0.2s ease-in-out;
  }
  div.entity-row state-badge {
    flex: 0 0 40px;
  }

  ha-dialog div.wrapper {
    margin-bottom: -20px;
  }

  ha-textfield {
    min-width: 220px;
  }

  a,
  a:visited {
    color: var(--primary-color);
  }

  ha-card settings-row:first-child,
  ha-card settings-row:first-of-type {
    border-top: 0px;
  }

  ha-card > ha-card {
    margin: 10px;
  }

  /* Common utility classes shared across views */
  .hidden {
    display: none;
  }

  /* Shared action button style (used instead of ha-button which may not load) */
  button.action-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background: var(--primary-color);
    border: none;
    border-radius: 4px;
    color: var(--text-primary-color, white);
    cursor: pointer;
    font-family: var(--mdc-typography-button-font-family, Roboto, sans-serif);
    font-size: 0.875rem;
    font-weight: 500;
    letter-spacing: 0.05em;
    padding: 8px 16px;
    text-transform: uppercase;
    transition: opacity 0.15s;
  }

  button.action-btn ha-icon {
    --mdc-icon-size: 18px;
    flex-shrink: 0;
  }

  button.action-btn:hover {
    opacity: 0.9;
  }

  button.action-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  button.action-btn.secondary {
    background: transparent;
    border: 1px solid var(--primary-color);
    color: var(--primary-color);
  }

  button.action-btn.secondary:hover {
    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
    opacity: 1;
  }

  /* Dialog footer row (replaces ha-dialog-footer) */
  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 16px 0 8px;
    margin-top: 8px;
    border-top: 1px solid var(--divider-color);
  }

  .dialog-btn {
    background: transparent;
    border: 1px solid var(--primary-color);
    border-radius: 4px;
    color: var(--primary-color);
    cursor: pointer;
    font-family: var(--mdc-typography-button-font-family, Roboto, sans-serif);
    font-size: 0.875rem;
    font-weight: 500;
    padding: 8px 16px;
    text-transform: uppercase;
    transition: background 0.15s;
  }

  .dialog-btn:hover {
    background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
  }

  .dialog-btn-primary {
    background: var(--primary-color);
    color: var(--text-primary-color, white);
    border-color: var(--primary-color);
  }

  .dialog-btn-primary:hover {
    opacity: 0.9;
    background: var(--primary-color);
  }

  .dialog-btn-primary:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .dialog-btn-danger {
    border-color: var(--error-color);
    color: var(--error-color);
  }

  .dialog-btn-danger:hover {
    background: rgba(var(--rgb-error-color, 244, 67, 54), 0.08);
  }

  .shortinput {
    width: 50px;
  }

  .loading-indicator {
    text-align: center;
    padding: 20px;
    color: var(--primary-text-color);
    font-style: italic;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }

  /* Lightweight CSS spinner — avoids depending on ha-circular-progress /
     ha-spinner, whose element name changed across HA versions. */
  .loading-indicator::before {
    content: "";
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 3px solid var(--divider-color, rgba(127, 127, 127, 0.3));
    border-top-color: var(--primary-color);
    animation: si-spin 0.8s linear infinite;
  }

  @keyframes si-spin {
    to {
      transform: rotate(360deg);
    }
  }

  .saving {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .saving-indicator {
    color: var(--primary-color);
    font-style: italic;
    margin-top: 8px;
    font-size: 0.9em;
  }

  /* Disabled input styling */
  button:disabled,
  select:disabled,
  input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  /* Common line/row layouts */
  .zoneline,
  .mappingsettingline,
  .schemaline {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 12px;
    align-items: center;
    margin-left: 0;
    margin-top: 8px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--divider-color);
    font-size: 0.9em;
  }

  .zoneline label,
  .mappingsettingline label,
  .schemaline label {
    color: var(--primary-text-color);
    font-weight: 500;
  }

  .zoneline input,
  .zoneline select,
  .mappingsettingline input,
  .mappingsettingline select,
  .schemaline input,
  .schemaline select {
    justify-self: end;
  }

  /* Common container styles */
  .zone,
  .mapping {
    margin-top: 25px;
    margin-bottom: 25px;
  }

  /* Mapping-specific container */
  .mappingline {
    margin-top: 16px;
    padding: 8px;
    border: 1px solid var(--divider-color);
    border-radius: 4px;
  }

  /* Note/alert styles - consolidated */
  .weather-note,
  .calendar-note,
  .info-note {
    padding: 8px;
    background: var(--secondary-background-color);
    color: var(--secondary-text-color);
    border-radius: 4px;
    font-size: 0.9em;
    font-style: italic;
  }

  .info-note {
    margin-top: 16px;
    background: var(--warning-color);
    color: var(--text-primary-color);
  }

  /* Radio button group styling */
  .radio-group {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin: 8px 0;
  }

  .radio-group label {
    display: flex;
    align-items: center;
    gap: 4px;
    cursor: pointer;
  }

  .radio-group input[type="radio"] {
    margin: 0;
  }

  input[type="radio"] {
    margin-right: 5px;
    margin-left: 10px;
  }

  input[type="radio"] + label {
    margin-right: 15px;
  }

  /* Common header styles */
  .subheader,
  .mappingsettingname {
    font-weight: bold;
  }

  /* Load more button styling */
  .load-more {
    text-align: center;
    padding: 16px;
  }

  .load-more button {
    background: var(--primary-color);
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
  }

  .load-more button:hover {
    background: var(--primary-color-dark, var(--primary-color));
  }

  /* Strikethrough utility */
  .strikethrough {
    text-decoration: line-through;
  }

  /* Information text styling */
  .information {
    margin-left: 20px;
    margin-top: 5px;
  }

  /* Calendar and weather table styles */
  .watering-calendar,
  .weather-records {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--divider-color);
  }

  .watering-calendar h4,
  .weather-records h4 {
    margin: 0 0 12px 0;
    font-size: 1em;
    font-weight: 500;
    color: var(--primary-text-color);
  }

  .calendar-table,
  .weather-table {
    display: grid;
    gap: 8px;
    font-size: 0.85em;
  }

  .calendar-table {
    grid-template-columns: 1fr 0.8fr 1fr 0.8fr 0.8fr;
  }

  .weather-table {
    grid-template-columns: 1fr 0.7fr 0.7fr 0.7fr 0.7fr 0.8fr 0.7fr 1fr;
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid var(--divider-color);
    border-radius: 4px;
  }

  .calendar-header,
  .weather-header {
    display: contents;
    font-weight: 500;
    color: var(--primary-text-color);
  }

  .calendar-header span,
  .weather-header span {
    padding: 4px;
    background: var(--card-background-color);
    border-bottom: 2px solid var(--primary-color);
  }

  .calendar-row,
  .weather-row {
    display: contents;
    color: var(--secondary-text-color);
  }

  .calendar-row span,
  .weather-row span {
    padding: 4px;
    border-bottom: 1px solid var(--divider-color);
  }

  .calendar-info {
    margin-top: 8px;
    padding: 4px 8px;
    background: var(--info-color, var(--primary-color));
    color: white;
    border-radius: 4px;
    font-size: 0.8em;
  }

  /* Zone info table styles */
  .zone-info-table {
    display: grid;
    grid-template-columns: 1fr;
    gap: 4px;
    margin-bottom: 16px;
  }

  .zone-info-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--divider-color);
    font-size: 0.9em;
  }

  .zone-info-label {
    color: var(--primary-text-color);
    font-weight: 500;
  }

  .zone-info-value {
    color: var(--secondary-text-color);
    text-align: right;
  }

  /* Info item styles */
  .info-item {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    align-items: center;
    margin-bottom: 8px;
    padding: 6px 8px;
    border-bottom: 1px solid var(--divider-color);
    font-size: 0.9em;
  }

  .info-item label {
    font-weight: 500;
    min-width: 120px;
    color: var(--primary-text-color);
  }

  .info-item .value {
    color: var(--secondary-text-color);
    font-family: monospace;
    text-align: right;
    justify-self: end;
  }

  .info-item.explanation {
    grid-template-columns: 1fr;
    align-items: flex-start;
  }

  .explanation-text {
    background: var(--card-background-color);
    border: 1px solid var(--divider-color);
    border-radius: 4px;
    padding: 8px;
    font-size: 0.9em;
    line-height: 1.4;
    white-space: pre-wrap;
    margin-top: 4px;
    width: 100%;
    box-sizing: border-box;
  }

  /* Action button containers for zones page */
  .action-buttons {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-top: 16px;
    padding: 12px 8px;
    border-top: 1px solid var(--divider-color);
  }

  .action-buttons-left,
  .action-buttons-right {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  /* Labeled action button - generic class for all pages */
  .action-button {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .action-button:hover {
    background-color: var(--secondary-background-color);
  }

  /* For zones page - left column has label on right of icon */
  .action-button-left {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    flex-direction: row;
  }

  /* For zones page - right column has label on left of icon */
  .action-button-right {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 8px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    text-align: right;
    justify-content: flex-end;
  }

  .action-button-left:hover,
  .action-button-right:hover {
    background-color: var(--secondary-background-color);
  }

  .action-button svg {
    flex-shrink: 0;
  }

  .action-button-label {
    font-size: 0.85em;
    color: var(--primary-text-color);
    white-space: nowrap;
  }
`;
  c`
  /* ha-dialog styles */
  ha-dialog {
    --mdc-dialog-min-width: 400px;
    --mdc-dialog-max-width: 600px;
    --mdc-dialog-heading-ink-color: var(--primary-text-color);
    --mdc-dialog-content-ink-color: var(--primary-text-color);
    --justify-action-buttons: space-between;
  }
  /* make dialog fullscreen on small screens */
  @media all and (max-width: 450px), all and (max-height: 500px) {
    ha-dialog {
      --mdc-dialog-min-width: calc(
        100vw - env(safe-area-inset-right) - env(safe-area-inset-left)
      );
      --mdc-dialog-max-width: calc(
        100vw - env(safe-area-inset-right) - env(safe-area-inset-left)
      );
      --mdc-dialog-min-height: 100%;
      --mdc-dialog-max-height: 100%;
      --vertial-align-dialog: flex-end;
      --ha-dialog-border-radius: 0px;
    }
  }
  ha-dialog div.description {
    margin-bottom: 10px;
  }
`;
  const Mn = e => String(e).padStart(2, "0");
  function Dn(e) {
    return e instanceof Date ? e : new Date(e);
  }
  function Cn(e) {
    const t = Dn(e);
    return `${Mn(t.getHours())}:${Mn(t.getMinutes())}`;
  }
  function Hn(e, t) {
    return e.getFullYear() === t.getFullYear() && e.getMonth() === t.getMonth() && e.getDate() === t.getDate();
  }
  class Ln extends Ae(de) {
    constructor() {
      super(...arguments), this.hideSettingsLinks = !1, this.actionsMode = "full", this.zones = [], this.isLoading = !0, this._initialLoadDone = !1, this.isSaving = !1, this._operationError = null, this._confirmIrrigate = null, this._skipDetailsOpen = !1, this._updateScheduled = !1;
    }
    _scheduleUpdate() {
      this._updateScheduled || (this._updateScheduled = !0, requestAnimationFrame(() => {
        this._updateScheduled = !1, this.requestUpdate();
      }));
    }
    firstUpdated() {
      _e().then(() => this._scheduleUpdate()).catch(e => {
        console.error("Failed to load HA form:", e), this._scheduleUpdate();
      });
    }
    hassSubscribe() {
      return this._fetchData().catch(e => {
        console.error("Failed to fetch initial data:", e);
      }), [this.hass.connection.subscribeMessage(() => {
        this._fetchData().catch(e => {
          console.error("Failed to fetch data on config update:", e);
        });
      }, {
        type: fe + "_config_updated"
      })];
    }
    async _fetchData() {
      if (!this.hass) return;
      const e = !this._initialLoadDone;
      try {
        e && (this.isLoading = !0);
        const [a, i, n] = await Promise.all([(t = this.hass, t.callWS({
          type: fe + "/config"
        })), ye(this.hass), we(this.hass).catch(e => {
          console.error("Failed to fetch irrigation outlook:", e);
        })]);
        this.config = a, this.zones = i, this._outlook = n, this._initialLoadDone = !0;
      } catch (e) {
        console.error("Error fetching data:", e), Tn(this, this.hass, "common.errors.load_failed", e);
      } finally {
        e && (this.isLoading = !1), this._scheduleUpdate();
      }
      var t;
    }
    handleCalculateAllZones() {
      var e;
      this.hass && (this.isSaving = !0, this._scheduleUpdate(), (e = this.hass, e.callApi("POST", fe + "/zones", {
        calculate_all: !0
      })).catch(e => {
        console.error("Failed to calculate all zones:", e), Tn(this, this.hass, "common.errors.action_failed", e);
      }).finally(() => {
        this.isSaving = !1, this._fetchData().catch(e => console.error("fetchData after calc-all:", e));
      }));
    }
    handleUpdateAllZones() {
      var e;
      this.hass && (this.isSaving = !0, this._scheduleUpdate(), (e = this.hass, e.callApi("POST", fe + "/zones", {
        update_all: !0
      })).catch(e => {
        console.error("Failed to update all zones:", e), Tn(this, this.hass, "common.errors.action_failed", e);
      }).finally(() => {
        this.isSaving = !1, this._fetchData().catch(e => console.error("fetchData after update-all:", e));
      }));
    }
    get _linkedZoneCount() {
      return this.zones.filter(e => {
        var t;
        return e.linked_entity && (null !== (t = e.duration) && void 0 !== t ? t : 0) > 0;
      }).length;
    }
    async _doIrrigate() {
      var e;
      const t = this._confirmIrrigate;
      if (this._confirmIrrigate = null, null === t || !this.hass) return;
      const a = "all" === t,
        i = a ? void 0 : this.zones.find(e => {
          var a;
          return (null === (a = e.id) || void 0 === a ? void 0 : a.toString()) === t;
        }),
        n = a ? `(${this._linkedZoneCount})` : `: ${null !== (e = null == i ? void 0 : i.name) && void 0 !== e ? e : t}`;
      try {
        await (r = this.hass, o = a ? void 0 : t, r.callWS(Object.assign({
          type: fe + "/irrigate_now"
        }, void 0 !== o ? {
          zone_id: o
        } : {}))), xn(this, `${wn("panels.zones.confirm_irrigate.toast_started", this.hass.language)} ${n}`);
      } catch (e) {
        const t = En(e);
        console.error("irrigate_now failed", e), xn(this, `${wn("panels.zones.confirm_irrigate.toast_failed", this.hass.language)}: ${t}`);
      }
      var r, o;
    }
    handleCalculateZone(e) {
      const t = this.zones[e];
      var a, i;
      t && null != t.id && this.hass && (this._operationError = null, this.isSaving = !0, this._scheduleUpdate(), (a = this.hass, i = t.id.toString(), a.callApi("POST", fe + "/zones", {
        id: i,
        calculate: !0,
        override_cache: !0
      })).catch(e => {
        const t = En(e);
        console.error("calculateZone failed:", e), this._operationError = t;
      }).finally(() => {
        this.isSaving = !1, this._fetchData().catch(e => console.error("fetchData after calc:", e));
      }));
    }
    handleUpdateZone(e) {
      const t = this.zones[e];
      var a, i;
      t && null != t.id && this.hass && (this._operationError = null, this.isSaving = !0, this._scheduleUpdate(), (a = this.hass, i = t.id.toString(), a.callApi("POST", fe + "/zones", {
        id: i,
        update: !0
      })).catch(e => {
        const t = En(e);
        console.error("updateZone failed:", e), this._operationError = t;
      }).finally(() => {
        this.isSaving = !1, this._fetchData().catch(e => console.error("fetchData after update:", e));
      }));
    }
    _openZoneSettings(e) {
      const t = void 0 !== e.id ? {
        params: {
          zone: String(e.id)
        }
      } : void 0;
      Sn(0, t ? jn("setup", "zones", t) : jn("setup", "zones"));
    }
    _runTargetsZone(e, t) {
      return "all" === e.zones || !(!Array.isArray(e.zones) || void 0 === t.id) && e.zones.map(e => Number(e)).includes(Number(t.id));
    }
    get _nextIrrigateRun() {
      var e;
      return null === (e = this._outlook) || void 0 === e ? void 0 : e.upcoming_runs.find(e => "irrigate" === e.action && e.next_run_utc);
    }
    _nextIrrigateRunForZone(e) {
      var t;
      return null === (t = this._outlook) || void 0 === t ? void 0 : t.upcoming_runs.find(t => "irrigate" === t.action && t.next_run_utc && this._runTargetsZone(t, e));
    }
    get _activeGuards() {
      var e, t;
      return null !== (t = null === (e = this._outlook) || void 0 === e ? void 0 : e.skip_preview.checks.filter(e => e.enabled)) && void 0 !== t ? t : [];
    }
    get _triggeredGuards() {
      return this._activeGuards.filter(e => e.would_skip);
    }
    _zoneHasDeficit(e) {
      var t, a, i;
      const n = null !== (t = e.duration) && void 0 !== t ? t : 0,
        r = Number(null !== (a = e.bucket) && void 0 !== a ? a : 0),
        o = Number(null !== (i = e.bucket_threshold) && void 0 !== i ? i : 0);
      return n > 0 && r < o;
    }
    _formatRunTime(e) {
      if (!this.hass) return "";
      const t = this.hass.language,
        a = new Date(e),
        i = Cn(a),
        n = new Date();
      return Hn(a, n) ? `${wn("panels.zones.outlook.today", t)} ${i}` : Hn(a, function (e, t) {
        const a = new Date(e.getTime());
        return a.setDate(a.getDate() + t), a;
      }(n, 1)) ? `${wn("panels.zones.outlook.tomorrow", t)} ${i}` : function (e, t) {
        const a = Dn(e);
        return `${new Intl.DateTimeFormat(t, {
          weekday: "short"
        }).format(a)} ${Cn(a)}`;
      }(a, t);
    }
    _guardLabel(e) {
      return wn(`panels.zones.outlook.checks.${e.id}`, this.hass.language);
    }
    _guardDetail(e) {
      var t;
      return e.available && null !== e.observed ? wn(`panels.zones.outlook.check_detail.${e.id}`, this.hass.language, "{observed}", String(e.observed), "{threshold}", String(null !== (t = e.threshold) && void 0 !== t ? t : "")) : "";
    }
    _renderSkipReasons() {
      const e = this.hass.language;
      return U`
      <div class="outlook-line outlook-skip-reasons">
        <ul class="skip-reasons">
          ${this._triggeredGuards.map(e => {
        const t = this._guardDetail(e);
        return U`<li>
              ${this._guardLabel(e)}${t ? U` — ${t}` : ""}
            </li>`;
      })}
        </ul>
      </div>
      <div class="outlook-line outlook-dim skip-reasons-note">
        ${wn("panels.zones.outlook.provisional", e)}
      </div>
    `;
    }
    _openSchedules() {
      Sn(0, jn("setup", "schedules"));
    }
    _runActionLabel(e) {
      return wn(`panels.zones.outlook.actions.${e.action}`, this.hass.language);
    }
    _runTargetsLabel(e) {
      const t = this.hass.language;
      if ("all" === e.zones) return wn("panels.zones.outlook.targets_all", t);
      const a = Array.isArray(e.zones) ? e.zones.length : 0;
      return wn("panels.zones.outlook.targets_zones", t, "{count}", String(a));
    }
    _renderOutlookBanner() {
      if (!this.hass || !this._outlook) return U``;
      const e = this.hass.language,
        t = this._nextIrrigateRun,
        a = this._triggeredGuards,
        i = this._outlook.last_skip_evaluation;
      return t && t.next_run_utc ? U`
      <ha-card class="outlook-card">
        <div class="outlook">
          <div class="outlook-line outlook-headline">
            <ha-icon icon="mdi:calendar-clock"></ha-icon>
            <span>
              <strong
                >${wn("panels.zones.outlook.next_run", e)}:</strong
              >
              ${this._runActionLabel(t)}
              ${this._formatRunTime(t.next_run_utc)}
              <span class="outlook-dim"
                >· ${t.name} · ${this._runTargetsLabel(t)}</span
              >
            </span>
          </div>

          ${a.length > 0 ? U`
                <div class="outlook-line outlook-skip">
                  <ha-icon icon="mdi:alert"></ha-icon>
                  <span
                    >${wn("panels.zones.outlook.will_skip", e)}</span
                  >
                  <button
                    class="outlook-info-btn"
                    aria-expanded="${this._skipDetailsOpen}"
                    title="${wn("panels.zones.outlook.why_skipped", e)}"
                    @click="${() => {
        this._skipDetailsOpen = !this._skipDetailsOpen;
      }}"
                  >
                    <ha-icon
                      icon="${this._skipDetailsOpen ? "mdi:chevron-up" : "mdi:information-outline"}"
                    ></ha-icon>
                    <span class="outlook-info-label"
                      >${wn("panels.zones.outlook.why_skipped", e)}</span
                    >
                  </button>
                </div>
                ${this._skipDetailsOpen ? this._renderSkipReasons() : ""}
              ` : U`
                <div class="outlook-line outlook-clear">
                  <ha-icon icon="mdi:check-circle-outline"></ha-icon>
                  <span
                    >${wn("panels.zones.outlook.will_run", e)}</span
                  >
                </div>
              `}
          ${i ? this._renderLastRunLine(i) : ""}
        </div>
      </ha-card>
    ` : U`
        <ha-card class="outlook-card">
          <div class="outlook">
            <div class="outlook-line outlook-headline">
              <ha-icon icon="mdi:calendar-alert"></ha-icon>
              <span>${wn("panels.zones.outlook.no_schedule", e)}</span>
              ${this.hideSettingsLinks ? "" : U`
                    <button
                      class="outlook-link"
                      @click="${this._openSchedules}"
                    >
                      ${wn("panels.zones.outlook.setup_schedule", e)}
                    </button>
                  `}
            </div>
            ${i ? this._renderLastRunLine(i) : ""}
          </div>
        </ha-card>
      `;
    }
    _renderLastRunLine(e) {
      const t = this.hass.language,
        a = function (e, t) {
          const a = Dn(e).getTime() - Date.now(),
            i = new Intl.RelativeTimeFormat(t, {
              numeric: "auto"
            }),
            n = Math.round(a / 1e3);
          if (Math.abs(n) < 60) return i.format(n, "second");
          const r = Math.round(n / 60);
          if (Math.abs(r) < 60) return i.format(r, "minute");
          const o = Math.round(r / 60);
          if (Math.abs(o) < 24) return i.format(o, "hour");
          const s = Math.round(o / 24);
          if (Math.abs(s) < 30) return i.format(s, "day");
          const l = Math.round(s / 30);
          return Math.abs(l) < 12 ? i.format(l, "month") : i.format(Math.round(l / 12), "year");
        }(e.timestamp, t),
        i = e.checks.filter(e => e.enabled && e.would_skip).map(e => this._guardLabel(e).toLowerCase()).join(", "),
        n = e.would_skip ? `${wn("panels.zones.outlook.last_run_skipped", t)}${i ? ` (${i})` : ""}` : wn("panels.zones.outlook.last_run_ran", t);
      return U`
      <div class="outlook-line outlook-last">
        <span class="outlook-dim"
          >${wn("panels.zones.outlook.last_run", t)}:</span
        >
        <span>${n} · ${a}</span>
      </div>
    `;
    }
    _renderZoneDecision(e) {
      var t;
      if (!this.hass) return U``;
      const a = this.hass.language,
        i = null !== (t = e.duration) && void 0 !== t ? t : 0;
      let n, r, o;
      if (e.state === Ee.Disabled) n = wn("panels.zones.status.decision_disabled", a), r = "neutral", o = "mdi:power-off";else if (e.last_calculated) {
        if (this._zoneHasDeficit(e)) {
          const t = function (e) {
              const t = Math.round(e);
              if (t < 60) return `${t} s`;
              const a = Math.floor(t / 60),
                i = t % 60;
              return i ? `${a} min ${i} s` : `${a} min`;
            }(i),
            s = this._triggeredGuards,
            l = this._nextIrrigateRunForZone(e);
          s.length > 0 ? (n = wn("panels.zones.status.decision_water_skip", a, "{duration}", t, "{reason}", this._guardLabel(s[0]).toLowerCase()), r = "skip", o = "mdi:weather-rainy") : l && l.next_run_utc ? (n = wn("panels.zones.status.decision_water_at", a, "{duration}", t, "{time}", this._formatRunTime(l.next_run_utc)), r = "water", o = "mdi:water") : (n = wn("panels.zones.status.decision_water_no_schedule", a, "{duration}", t), r = "water", o = "mdi:water-alert");
        } else n = wn("panels.zones.status.decision_no_water", a), r = "ok", o = "mdi:check-circle-outline";
      } else n = wn("panels.zones.status.decision_unknown", a), r = "unknown", o = "mdi:help-circle-outline";
      return U`
      <div class="zone-decision ${r}">
        <ha-icon icon="${o}"></ha-icon>
        <span>${n}</span>
      </div>
    `;
    }
    _zoneEstimate(e) {
      var t, a;
      if (void 0 !== e.id) return null === (a = null === (t = this._outlook) || void 0 === t ? void 0 : t.zone_estimates) || void 0 === a ? void 0 : a[String(e.id)];
    }
    _renderZoneEstimate(e) {
      if (!this.hass) return U``;
      const t = this._zoneEstimate(e);
      if (!t || !t.available || null == t.live_deficit) return U``;
      const a = this.hass.language,
        i = An(this.config, ze),
        n = t.live_deficit < 0 ? "var(--warning-color)" : "var(--success-color)",
        r = wn(`panels.zones.status.estimate_method.${"proxy" === t.method ? "proxy" : "hourly"}`, a) + (t.as_of ? ` · ${Cn(t.as_of)}` : "");
      return U`
      <span class="status-sep">·</span>
      <span class="zone-estimate" title="${r}">
        ${wn("panels.zones.status.estimate_now", a)}
        <strong style="color: ${n}"
          >≈ ${t.live_deficit.toFixed(2)} ${i}</strong
        >
        <span class="estimate-tag"
          >${wn("panels.zones.status.estimate_tag", a)}</span
        >
      </span>
    `;
    }
    _renderZoneNextRun(e) {
      if (!this.hass) return U``;
      const t = this._nextIrrigateRunForZone(e);
      if (!t || !t.next_run_utc) return U``;
      return e.state !== Ee.Disabled && e.last_calculated && this._zoneHasDeficit(e) && 0 === this._triggeredGuards.length ? U`` : U`
      <span class="status-sep">·</span>
      <span>
        ${wn("panels.zones.outlook.next_run", this.hass.language)}:
        <strong>${this._formatRunTime(t.next_run_utc)}</strong>
      </span>
    `;
    }
    renderZone(e, t) {
      var a, i;
      if (!this.hass) return U``;
      const n = Number(null !== (a = e.bucket) && void 0 !== a ? a : 0),
        r = n < 0 ? "var(--warning-color)" : "var(--success-color)",
        o = e.state === Ee.Automatic ? "state-automatic" : e.state === Ee.Manual ? "state-manual" : "state-disabled",
        s = e.last_calculated ? function (e) {
          const t = Dn(e);
          return `${t.getFullYear()}-${Mn(t.getMonth() + 1)}-${Mn(t.getDate())} ${Mn(t.getHours())}:${Mn(t.getMinutes())}`;
        }(e.last_calculated) : wn("panels.zones.status.never", this.hass.language);
      return U`
      <ha-card>
        <div class="card-header">
          <div class="name">${e.name}</div>
          <span class="zone-state-badge ${o}">
            ${wn(`panels.zones.labels.states.${e.state}`, this.hass.language)}
          </span>
          ${this.hideSettingsLinks ? "" : U`
                <ha-icon-button
                  .path="${"M12,15.5A3.5,3.5 0 0,1 8.5,12A3.5,3.5 0 0,1 12,8.5A3.5,3.5 0 0,1 15.5,12A3.5,3.5 0 0,1 12,15.5M19.43,12.97C19.47,12.65 19.5,12.33 19.5,12C19.5,11.67 19.47,11.34 19.43,11L21.54,9.37C21.73,9.22 21.78,8.95 21.66,8.73L19.66,5.27C19.54,5.05 19.27,4.96 19.05,5.05L16.56,6.05C16.04,5.66 15.5,5.32 14.87,5.07L14.5,2.42C14.46,2.18 14.25,2 14,2H10C9.75,2 9.54,2.18 9.5,2.42L9.13,5.07C8.5,5.32 7.96,5.66 7.44,6.05L4.95,5.05C4.73,4.96 4.46,5.05 4.34,5.27L2.34,8.73C2.21,8.95 2.27,9.22 2.46,9.37L4.57,11C4.53,11.34 4.5,11.67 4.5,12C4.5,12.33 4.53,12.65 4.57,12.97L2.46,14.63C2.27,14.78 2.21,15.05 2.34,15.27L4.34,18.73C4.46,18.95 4.73,19.03 4.95,18.95L7.44,17.94C7.96,18.34 8.5,18.68 9.13,18.93L9.5,21.58C9.54,21.82 9.75,22 10,22H14C14.25,22 14.46,21.82 14.5,21.58L14.87,18.93C15.5,18.67 16.04,18.34 16.56,17.94L19.05,18.95C19.27,19.03 19.54,18.95 19.66,18.73L21.66,15.27C21.78,15.05 21.73,14.78 21.54,14.63L19.43,12.97Z"}"
                  title="${wn("panels.zones.actions.open_settings", this.hass.language)}"
                  @click="${() => this._openZoneSettings(e)}"
                ></ha-icon-button>
              `}
        </div>

        <!-- AT-A-GLANCE DECISION -->
        ${this._renderZoneDecision(e)}

        <!-- COMPACT STATUS -->
        <div class="card-content">
          <div class="zone-status-line">
            <span
              title="${wn("panels.zones.help.bucket", this.hass.language)}"
            >
              ${wn("panels.zones.labels.bucket", this.hass.language)}:
              <strong style="color: ${r}"
                >${n.toFixed(2)}
                ${An(this.config, ze)}</strong
              >
            </span>
            <span class="status-sep">·</span>
            <span>
              ${wn("panels.zones.status.last_checked", this.hass.language)}:
              <strong>${s}</strong>
            </span>
            ${this._renderZoneEstimate(e)} ${this._renderZoneNextRun(e)}
          </div>
        </div>

        <!-- ACTION BUTTONS -->
        <div class="card-content zone-action-bar">
          ${"full" === this.actionsMode && e.state === Ee.Automatic ? U`
                <button
                  class="action-btn"
                  title="${wn("panels.zones.help.update", this.hass.language)}"
                  @click="${() => this.handleUpdateZone(t)}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon icon="mdi:update"></ha-icon>
                  ${wn("panels.zones.actions.update", this.hass.language)}
                </button>
                <button
                  class="action-btn"
                  title="${wn("panels.zones.help.calculate", this.hass.language)}"
                  @click="${() => this.handleCalculateZone(t)}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon icon="mdi:calculator"></ha-icon>
                  ${wn("panels.zones.actions.calculate", this.hass.language)}
                </button>
              ` : ""}
          ${"none" !== this.actionsMode && e.linked_entity && (null !== (i = e.duration) && void 0 !== i ? i : 0) > 0 ? U`
                <button
                  class="action-btn"
                  raised
                  @click="${() => {
        void 0 !== e.id && (this._confirmIrrigate = e.id.toString());
      }}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon icon="mdi:water"></ha-icon>
                  ${wn("panels.zones.labels.irrigate_now", this.hass.language)}
                </button>
              ` : e.linked_entity ? "" : U`
                  <button
                    class="action-btn"
                    disabled
                    title="${wn("panels.zones.help.irrigate_link_entity", this.hass.language)}"
                  >
                    <ha-icon icon="mdi:water"></ha-icon>
                    ${wn("panels.zones.labels.irrigate_now", this.hass.language)}
                  </button>
                  <span class="zones-top-note">
                    ${wn("panels.zones.help.irrigate_link_entity", this.hass.language)}
                  </span>
                `}
        </div>
      </ha-card>
    `;
    }
    render() {
      var e, t;
      if (!this.hass) return U``;
      if (this.isLoading) return U`
        <ha-card header="${wn("panels.zones.title", this.hass.language)}">
          <div class="card-content">
            <div class="loading-indicator">
              ${wn("common.loading-messages.general", this.hass.language)}
            </div>
          </div>
        </ha-card>
      `;
      const a = this.zones.some(e => {
          var t;
          return e.linked_entity && (null !== (t = e.duration) && void 0 !== t ? t : 0) > 0;
        }),
        i = 0 === this.zones.length;
      return U`
      ${i ? this.hideSettingsLinks ? U`
              <ha-card>
                <div class="card-content description-text">
                  ${wn("panels.zones.no_items", this.hass.language)}
                </div>
              </ha-card>
            ` : U`
              <ha-card class="setup-banner-card">
                <div class="setup-banner">
                  <div class="setup-banner-icon">🌱</div>
                  <div class="setup-banner-content">
                    <div class="setup-banner-title">
                      ${wn("wizard.title", this.hass.language)}
                    </div>
                    <div class="setup-banner-desc">
                      ${wn("wizard.setup_complete_banner", this.hass.language)}
                    </div>
                  </div>
                  <button
                    class="action-btn setup-banner-btn"
                    @click="${() => {
        this.dispatchEvent(new CustomEvent("open-wizard", {
          bubbles: !0,
          composed: !0
        }));
      }}"
                  >
                    ${wn("wizard.open_wizard", this.hass.language)}
                  </button>
                </div>
              </ha-card>
            ` : ""}
      ${i ? "" : this._renderOutlookBanner()}

      <!-- Zones header card: run-all operational actions -->
      <ha-card>
        <div class="card-header">
          <div class="name">
            ${wn("panels.zones.title", this.hass.language)}
          </div>
        </div>
        <div class="card-content zones-top-actions">
          ${"full" === this.actionsMode ? U`
                <button
                  class="action-btn"
                  title="${wn("panels.zones.help.update_all", this.hass.language)}"
                  @click="${this.handleUpdateAllZones}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon icon="mdi:update"></ha-icon>
                  ${wn("panels.zones.cards.zone-actions.actions.update-all", this.hass.language)}
                </button>
                <button
                  class="action-btn"
                  title="${wn("panels.zones.help.calculate_all", this.hass.language)}"
                  @click="${this.handleCalculateAllZones}"
                  ?disabled="${this.isSaving}"
                >
                  <ha-icon icon="mdi:calculator"></ha-icon>
                  ${wn("panels.zones.cards.zone-actions.actions.calculate-all", this.hass.language)}
                </button>
              ` : ""}
          ${"none" !== this.actionsMode ? U`
                <button
                  class="action-btn"
                  raised
                  title="${wn("panels.zones.help.irrigate_all", this.hass.language)}"
                  @click="${() => {
        this._confirmIrrigate = "all";
      }}"
                  ?disabled="${!a || this.isSaving}"
                >
                  <ha-icon icon="mdi:water"></ha-icon>
                  ${wn("panels.zones.actions.irrigate_all", this.hass.language)}
                </button>
              ` : ""}
          ${a ? "" : U`<span class="zones-top-note"
                >${wn("panels.info.cards.irrigate_now.no_linked_zones", this.hass.language)}</span
              >`}
        </div>
      </ha-card>

      <!-- Irrigate confirmation dialog -->
      ${null !== this._confirmIrrigate ? U`
            <ha-dialog
              open
              @closed="${() => {
        this._confirmIrrigate = null;
      }}"
              heading="${wn("panels.zones.confirm_irrigate.title", this.hass.language)}"
            >
              <p>
                ${wn("panels.zones.confirm_irrigate.body", this.hass.language)}
              </p>
              <p>
                <strong>
                  ${"all" === this._confirmIrrigate ? `${wn("panels.zones.confirm_irrigate.all_linked_zones", this.hass.language)} (${this._linkedZoneCount})` : null !== (t = null === (e = this.zones.find(e => {
        var t;
        return (null === (t = e.id) || void 0 === t ? void 0 : t.toString()) === this._confirmIrrigate;
      })) || void 0 === e ? void 0 : e.name) && void 0 !== t ? t : this._confirmIrrigate}
                </strong>
              </p>
              <div class="dialog-footer">
                <button
                  class="dialog-btn"
                  @click="${() => {
        this._confirmIrrigate = null;
      }}"
                >
                  ${wn("common.actions.cancel", this.hass.language)}
                </button>
                <button
                  class="dialog-btn dialog-btn-primary"
                  @click="${this._doIrrigate}"
                >
                  ${wn("panels.zones.labels.irrigate_now", this.hass.language)}
                </button>
              </div>
            </ha-dialog>
          ` : ""}

      <!-- Operation error banner -->
      ${this._operationError ? U`
            <ha-card class="error-banner-card">
              <div class="error-banner">
                <ha-icon
                  class="error-banner-icon"
                  icon="mdi:alert-circle-outline"
                ></ha-icon>
                <span class="error-banner-msg">${this._operationError}</span>
                <ha-icon-button
                  .path="${"M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z"}"
                  @click="${() => {
        this._operationError = null;
      }}"
                  aria-label="${wn("common.actions.cancel", this.hass.language)}"
                ></ha-icon-button>
              </div>
            </ha-card>
          ` : ""}

      <!-- Zone cards -->
      ${this.zones.map((e, t) => this.renderZone(e, t))}
    `;
    }
    static get styles() {
      return c`
      ${Pn}

      /* At-a-glance decision line */
      .zone-decision {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 0 16px 12px;
        padding: 10px 12px;
        border-radius: 8px;
        font-size: 0.9rem;
        font-weight: 500;
        line-height: 1.35;
      }

      .zone-decision ha-icon {
        flex-shrink: 0;
        --mdc-icon-size: 22px;
      }

      .zone-decision.water {
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12);
        color: var(--primary-color);
      }

      .zone-decision.ok {
        background: rgba(76, 175, 80, 0.12);
        color: var(--success-color, #2e7d32);
      }

      .zone-decision.neutral {
        background: var(--secondary-background-color);
        color: var(--secondary-text-color);
      }

      .zone-decision.unknown {
        background: rgba(255, 152, 0, 0.12);
        color: var(--warning-color, #ed6c02);
      }

      .zone-decision.skip {
        background: rgba(255, 152, 0, 0.12);
        color: var(--warning-color, #ed6c02);
      }

      /* Global outlook banner */
      .outlook-card {
        border-left: 4px solid var(--primary-color);
      }

      .outlook {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 14px 16px;
      }

      .outlook-line {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        font-size: 0.875rem;
        line-height: 1.35;
      }

      .outlook-line ha-icon {
        flex-shrink: 0;
        --mdc-icon-size: 20px;
      }

      .outlook-headline {
        font-size: 0.95rem;
      }

      .outlook-headline ha-icon {
        color: var(--primary-color);
      }

      .outlook-skip {
        color: var(--warning-color, #ed6c02);
      }

      .outlook-clear {
        color: var(--success-color, #2e7d32);
      }

      .outlook-dim {
        color: var(--secondary-text-color);
        font-weight: 400;
      }

      /* Tap-to-expand "why it will skip" toggle (works on touch + desktop) */
      .outlook-info-btn {
        display: inline-flex;
        align-items: center;
        gap: 2px;
        background: transparent;
        border: none;
        color: var(--warning-color, #ed6c02);
        cursor: pointer;
        font: inherit;
        padding: 4px 6px;
        border-radius: 6px;
      }

      .outlook-info-btn:hover {
        background: rgba(255, 152, 0, 0.12);
      }

      .outlook-info-btn ha-icon {
        --mdc-icon-size: 18px;
      }

      .outlook-info-label {
        font-size: 0.8125rem;
        text-decoration: underline;
      }

      /* Expanded skip reasons */
      .outlook-skip-reasons {
        color: var(--warning-color, #ed6c02);
      }

      .skip-reasons {
        margin: 0;
        padding-left: 18px;
        font-size: 0.85rem;
      }

      .skip-reasons li {
        margin: 2px 0;
      }

      .skip-reasons-note {
        font-size: 0.8rem;
        font-style: italic;
      }

      .outlook-link {
        background: transparent;
        border: none;
        color: var(--primary-color);
        cursor: pointer;
        font-family: inherit;
        font-size: 0.875rem;
        font-weight: 500;
        padding: 0;
        text-decoration: underline;
      }

      /* Compact one-line status */
      .zone-status-line {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 6px;
        font-size: 0.875rem;
        color: var(--secondary-text-color);
      }

      .zone-status-line strong {
        color: var(--primary-text-color);
        font-weight: 500;
      }

      .status-sep {
        opacity: 0.5;
      }

      /* Read-only "live" estimate chip */
      .zone-estimate {
        cursor: help;
      }

      .estimate-tag {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.65;
      }

      /* Action bar */
      .zone-action-bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-top: 0;
        padding-bottom: 12px;
      }

      /* State badge */
      .zone-state-badge {
        font-size: 0.75rem;
        font-weight: 500;
        padding: 2px 8px;
        border-radius: 12px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        align-self: center;
        margin-left: auto;
      }

      .state-automatic {
        background: var(--success-color, #4caf50);
        color: white;
      }

      .state-manual {
        background: var(--accent-color, var(--primary-color));
        color: white;
      }

      .state-disabled {
        background: var(--disabled-color, #bdbdbd);
        color: white;
      }

      /* First-time setup banner */
      .setup-banner-card {
        border-left: 4px solid var(--primary-color);
      }

      .setup-banner {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 16px;
        flex-wrap: wrap;
      }

      .setup-banner-icon {
        font-size: 2rem;
        flex-shrink: 0;
      }

      .setup-banner-content {
        flex: 1;
        min-width: 180px;
      }

      .setup-banner-title {
        font-weight: 600;
        font-size: 0.95rem;
        color: var(--primary-text-color);
        margin-bottom: 4px;
      }

      .setup-banner-desc {
        font-size: 0.83rem;
        color: var(--secondary-text-color);
      }

      .setup-banner-btn {
        flex-shrink: 0;
      }

      .zones-top-actions {
        display: flex;
        align-items: center;
        gap: 12px;
        flex-wrap: wrap;
      }

      .zones-top-note {
        font-size: 0.8125rem;
        color: var(--secondary-text-color);
        font-style: italic;
      }

      /* Dialog footer buttons */
      .dialog-footer {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        padding: 16px 0 8px;
        margin-top: 8px;
        border-top: 1px solid var(--divider-color);
      }

      .dialog-btn {
        background: transparent;
        border: 1px solid var(--primary-color);
        border-radius: 4px;
        color: var(--primary-color);
        cursor: pointer;
        font-family: inherit;
        font-size: 0.875rem;
        font-weight: 500;
        padding: 8px 16px;
        transition: background 0.15s;
      }

      .dialog-btn:hover {
        background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.08);
      }

      .dialog-btn-primary {
        background: var(--primary-color);
        color: var(--text-primary-color, white);
      }

      .dialog-btn-primary:hover {
        opacity: 0.9;
        background: var(--primary-color);
      }

      /* Operation error banner */
      .error-banner-card {
        border-left: 4px solid var(--error-color, #f44336);
      }

      .error-banner {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 8px 8px 16px;
      }

      .error-banner-icon {
        color: var(--error-color, #f44336);
        flex-shrink: 0;
      }

      .error-banner-msg {
        flex: 1;
        color: var(--error-color, #f44336);
        font-size: 0.9rem;
        line-height: 1.4;
      }
    `;
    }
  }
  n([pe()], Ln.prototype, "config", void 0), n([pe({
    type: Boolean
  })], Ln.prototype, "hideSettingsLinks", void 0), n([pe({
    attribute: !1
  })], Ln.prototype, "actionsMode", void 0), n([pe({
    type: Array
  })], Ln.prototype, "zones", void 0), n([me()], Ln.prototype, "_outlook", void 0), n([pe({
    type: Boolean
  })], Ln.prototype, "isLoading", void 0), n([pe({
    type: Boolean
  })], Ln.prototype, "isSaving", void 0), n([me()], Ln.prototype, "_operationError", void 0), n([me()], Ln.prototype, "_confirmIrrigate", void 0), n([me()], Ln.prototype, "_skipDetailsOpen", void 0), customElements.get("smart-irrigation-view-zones") || customElements.define("smart-irrigation-view-zones", Ln);
  class Bn extends de {
    setConfig(e) {
      this._config = e;
    }
    getCardSize() {
      return 6;
    }
    static getStubConfig() {
      return {};
    }
    render() {
      var e;
      if (!this.hass || !this._config) return U``;
      const t = null !== (e = this._config.actions) && void 0 !== e ? e : "irrigate";
      return U`
      <smart-irrigation-view-zones
        .hass=${this.hass}
        .hideSettingsLinks=${!0}
        .actionsMode=${t}
      ></smart-irrigation-view-zones>
    `;
    }
  }
  n([pe({
    attribute: !1
  })], Bn.prototype, "hass", void 0), n([me()], Bn.prototype, "_config", void 0), customElements.get("smart-irrigation-zones-card") || customElements.define("smart-irrigation-zones-card", Bn);
  const Nn = window;
  Nn.customCards = Nn.customCards || [], Nn.customCards.some(e => "smart-irrigation-zones-card" === e.type) || (Nn.customCards.push({
    type: "smart-irrigation-zones-card",
    name: "Smart Irrigation Zones",
    description: "Everyday zone status and manual irrigation, usable by non-admin users.",
    preview: !1
  }), console.info(`%c smart-irrigation-zones-card %c ${be} `, "color: white; background: #3949ab; font-weight: 700;", "color: #3949ab; background: white; font-weight: 700;")), e.SmartIrrigationZonesCard = Bn, Object.defineProperty(e, "__esModule", {
    value: !0
  });
}({});
