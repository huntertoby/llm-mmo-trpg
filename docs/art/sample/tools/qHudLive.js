// 自動產生，不要手改：現行 HUD 圖示的畫法（client/src/world/HudBarIcons.tsx、HudIcons.tsx、ui/BattleToolIcons.tsx、SettingsHead.tsx、CreateIcons.tsx 的 RegionCrest 與 regionTheme.ts、render/skillIcon.ts 的 cardGlyphCanvas，用 vite 的 lib 模式打包成 IIFE，minify 關閉）。
// 只給 Q 版小圖示第 7 批樣張（q-icons-hud.html）的「現行」那一欄用，和實機同一份程式。React 元件用 react-dom/server 的 renderToStaticMarkup 輸出 SVG 字串：QHudLive.bar(k, px)、hud(name, px)、tool(name, px)、settings(icon)、crest(region, px)、accent(region)、cardGlyphCanvas(id, px, res, opt)。
// 重新產生：做法見 docs/art/Q版小圖示-第7批HUD.md 第 8 節（進入點 import 上面幾個元件掛到 window.QHudLive，用主資料夾 client/node_modules 的 vite build：lib、iife、pixi.js external；react、react-dom、yaml 用 alias 指到主資料夾 node_modules）。注意：載入時 regionTheme.ts 會在 <html> 掛區域主題的 CSS 變數（副作用，不影響樣張）。
(function() {
	//#region \0rolldown/runtime.js
	var __commonJSMin = (cb, mod) => () => (mod || (cb((mod = { exports: {} }).exports, mod, mod.exports), cb = null), mod.exports);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react@18.3.1/node_modules/react/cjs/react.production.min.js
	/**
	* @license React
	* react.production.min.js
	*
	* Copyright (c) Facebook, Inc. and its affiliates.
	*
	* This source code is licensed under the MIT license found in the
	* LICENSE file in the root directory of this source tree.
	*/
	var require_react_production_min = /* @__PURE__ */ __commonJSMin(((exports) => {
		var l = Symbol.for("react.element");
		var n = Symbol.for("react.portal");
		var p = Symbol.for("react.fragment");
		var q = Symbol.for("react.strict_mode");
		var r = Symbol.for("react.profiler");
		var t = Symbol.for("react.provider");
		var u = Symbol.for("react.context");
		var v = Symbol.for("react.forward_ref");
		var w = Symbol.for("react.suspense");
		var x = Symbol.for("react.memo");
		var y = Symbol.for("react.lazy");
		var z = Symbol.iterator;
		function A(a) {
			if (null === a || "object" !== typeof a) return null;
			a = z && a[z] || a["@@iterator"];
			return "function" === typeof a ? a : null;
		}
		var B = {
			isMounted: function() {
				return !1;
			},
			enqueueForceUpdate: function() {},
			enqueueReplaceState: function() {},
			enqueueSetState: function() {}
		};
		var C = Object.assign;
		var D = {};
		function E(a, b, e) {
			this.props = a;
			this.context = b;
			this.refs = D;
			this.updater = e || B;
		}
		E.prototype.isReactComponent = {};
		E.prototype.setState = function(a, b) {
			if ("object" !== typeof a && "function" !== typeof a && null != a) throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
			this.updater.enqueueSetState(this, a, b, "setState");
		};
		E.prototype.forceUpdate = function(a) {
			this.updater.enqueueForceUpdate(this, a, "forceUpdate");
		};
		function F() {}
		F.prototype = E.prototype;
		function G(a, b, e) {
			this.props = a;
			this.context = b;
			this.refs = D;
			this.updater = e || B;
		}
		var H = G.prototype = new F();
		H.constructor = G;
		C(H, E.prototype);
		H.isPureReactComponent = !0;
		var I = Array.isArray;
		var J = Object.prototype.hasOwnProperty;
		var K = { current: null };
		var L = {
			key: !0,
			ref: !0,
			__self: !0,
			__source: !0
		};
		function M(a, b, e) {
			var d, c = {}, k = null, h = null;
			if (null != b) for (d in void 0 !== b.ref && (h = b.ref), void 0 !== b.key && (k = "" + b.key), b) J.call(b, d) && !L.hasOwnProperty(d) && (c[d] = b[d]);
			var g = arguments.length - 2;
			if (1 === g) c.children = e;
			else if (1 < g) {
				for (var f = Array(g), m = 0; m < g; m++) f[m] = arguments[m + 2];
				c.children = f;
			}
			if (a && a.defaultProps) for (d in g = a.defaultProps, g) void 0 === c[d] && (c[d] = g[d]);
			return {
				$$typeof: l,
				type: a,
				key: k,
				ref: h,
				props: c,
				_owner: K.current
			};
		}
		function N(a, b) {
			return {
				$$typeof: l,
				type: a.type,
				key: b,
				ref: a.ref,
				props: a.props,
				_owner: a._owner
			};
		}
		function O(a) {
			return "object" === typeof a && null !== a && a.$$typeof === l;
		}
		function escape(a) {
			var b = {
				"=": "=0",
				":": "=2"
			};
			return "$" + a.replace(/[=:]/g, function(a) {
				return b[a];
			});
		}
		var P = /\/+/g;
		function Q(a, b) {
			return "object" === typeof a && null !== a && null != a.key ? escape("" + a.key) : b.toString(36);
		}
		function R(a, b, e, d, c) {
			var k = typeof a;
			if ("undefined" === k || "boolean" === k) a = null;
			var h = !1;
			if (null === a) h = !0;
			else switch (k) {
				case "string":
				case "number":
					h = !0;
					break;
				case "object": switch (a.$$typeof) {
					case l:
					case n: h = !0;
				}
			}
			if (h) return h = a, c = c(h), a = "" === d ? "." + Q(h, 0) : d, I(c) ? (e = "", null != a && (e = a.replace(P, "$&/") + "/"), R(c, b, e, "", function(a) {
				return a;
			})) : null != c && (O(c) && (c = N(c, e + (!c.key || h && h.key === c.key ? "" : ("" + c.key).replace(P, "$&/") + "/") + a)), b.push(c)), 1;
			h = 0;
			d = "" === d ? "." : d + ":";
			if (I(a)) for (var g = 0; g < a.length; g++) {
				k = a[g];
				var f = d + Q(k, g);
				h += R(k, b, e, f, c);
			}
			else if (f = A(a), "function" === typeof f) for (a = f.call(a), g = 0; !(k = a.next()).done;) k = k.value, f = d + Q(k, g++), h += R(k, b, e, f, c);
			else if ("object" === k) throw b = String(a), Error("Objects are not valid as a React child (found: " + ("[object Object]" === b ? "object with keys {" + Object.keys(a).join(", ") + "}" : b) + "). If you meant to render a collection of children, use an array instead.");
			return h;
		}
		function S(a, b, e) {
			if (null == a) return a;
			var d = [], c = 0;
			R(a, d, "", "", function(a) {
				return b.call(e, a, c++);
			});
			return d;
		}
		function T(a) {
			if (-1 === a._status) {
				var b = a._result;
				b = b();
				b.then(function(b) {
					if (0 === a._status || -1 === a._status) a._status = 1, a._result = b;
				}, function(b) {
					if (0 === a._status || -1 === a._status) a._status = 2, a._result = b;
				});
				-1 === a._status && (a._status = 0, a._result = b);
			}
			if (1 === a._status) return a._result.default;
			throw a._result;
		}
		var U = { current: null };
		var V = { transition: null };
		var W = {
			ReactCurrentDispatcher: U,
			ReactCurrentBatchConfig: V,
			ReactCurrentOwner: K
		};
		function X() {
			throw Error("act(...) is not supported in production builds of React.");
		}
		exports.Children = {
			map: S,
			forEach: function(a, b, e) {
				S(a, function() {
					b.apply(this, arguments);
				}, e);
			},
			count: function(a) {
				var b = 0;
				S(a, function() {
					b++;
				});
				return b;
			},
			toArray: function(a) {
				return S(a, function(a) {
					return a;
				}) || [];
			},
			only: function(a) {
				if (!O(a)) throw Error("React.Children.only expected to receive a single React element child.");
				return a;
			}
		};
		exports.Component = E;
		exports.Fragment = p;
		exports.Profiler = r;
		exports.PureComponent = G;
		exports.StrictMode = q;
		exports.Suspense = w;
		exports.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = W;
		exports.act = X;
		exports.cloneElement = function(a, b, e) {
			if (null === a || void 0 === a) throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + a + ".");
			var d = C({}, a.props), c = a.key, k = a.ref, h = a._owner;
			if (null != b) {
				void 0 !== b.ref && (k = b.ref, h = K.current);
				void 0 !== b.key && (c = "" + b.key);
				if (a.type && a.type.defaultProps) var g = a.type.defaultProps;
				for (f in b) J.call(b, f) && !L.hasOwnProperty(f) && (d[f] = void 0 === b[f] && void 0 !== g ? g[f] : b[f]);
			}
			var f = arguments.length - 2;
			if (1 === f) d.children = e;
			else if (1 < f) {
				g = Array(f);
				for (var m = 0; m < f; m++) g[m] = arguments[m + 2];
				d.children = g;
			}
			return {
				$$typeof: l,
				type: a.type,
				key: c,
				ref: k,
				props: d,
				_owner: h
			};
		};
		exports.createContext = function(a) {
			a = {
				$$typeof: u,
				_currentValue: a,
				_currentValue2: a,
				_threadCount: 0,
				Provider: null,
				Consumer: null,
				_defaultValue: null,
				_globalName: null
			};
			a.Provider = {
				$$typeof: t,
				_context: a
			};
			return a.Consumer = a;
		};
		exports.createElement = M;
		exports.createFactory = function(a) {
			var b = M.bind(null, a);
			b.type = a;
			return b;
		};
		exports.createRef = function() {
			return { current: null };
		};
		exports.forwardRef = function(a) {
			return {
				$$typeof: v,
				render: a
			};
		};
		exports.isValidElement = O;
		exports.lazy = function(a) {
			return {
				$$typeof: y,
				_payload: {
					_status: -1,
					_result: a
				},
				_init: T
			};
		};
		exports.memo = function(a, b) {
			return {
				$$typeof: x,
				type: a,
				compare: void 0 === b ? null : b
			};
		};
		exports.startTransition = function(a) {
			var b = V.transition;
			V.transition = {};
			try {
				a();
			} finally {
				V.transition = b;
			}
		};
		exports.unstable_act = X;
		exports.useCallback = function(a, b) {
			return U.current.useCallback(a, b);
		};
		exports.useContext = function(a) {
			return U.current.useContext(a);
		};
		exports.useDebugValue = function() {};
		exports.useDeferredValue = function(a) {
			return U.current.useDeferredValue(a);
		};
		exports.useEffect = function(a, b) {
			return U.current.useEffect(a, b);
		};
		exports.useId = function() {
			return U.current.useId();
		};
		exports.useImperativeHandle = function(a, b, e) {
			return U.current.useImperativeHandle(a, b, e);
		};
		exports.useInsertionEffect = function(a, b) {
			return U.current.useInsertionEffect(a, b);
		};
		exports.useLayoutEffect = function(a, b) {
			return U.current.useLayoutEffect(a, b);
		};
		exports.useMemo = function(a, b) {
			return U.current.useMemo(a, b);
		};
		exports.useReducer = function(a, b, e) {
			return U.current.useReducer(a, b, e);
		};
		exports.useRef = function(a) {
			return U.current.useRef(a);
		};
		exports.useState = function(a) {
			return U.current.useState(a);
		};
		exports.useSyncExternalStore = function(a, b, e) {
			return U.current.useSyncExternalStore(a, b, e);
		};
		exports.useTransition = function() {
			return U.current.useTransition();
		};
		exports.version = "18.3.1";
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react@18.3.1/node_modules/react/index.js
	var require_react = /* @__PURE__ */ __commonJSMin(((exports, module) => {
		module.exports = require_react_production_min();
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react-dom@18.3.1_react@18.3.1/node_modules/react-dom/cjs/react-dom-server-legacy.browser.production.min.js
	/**
	* @license React
	* react-dom-server-legacy.browser.production.min.js
	*
	* Copyright (c) Facebook, Inc. and its affiliates.
	*
	* This source code is licensed under the MIT license found in the
	* LICENSE file in the root directory of this source tree.
	*/
	var require_react_dom_server_legacy_browser_production_min = /* @__PURE__ */ __commonJSMin(((exports) => {
		var aa = require_react();
		function l(a) {
			for (var b = "https://reactjs.org/docs/error-decoder.html?invariant=" + a, c = 1; c < arguments.length; c++) b += "&args[]=" + encodeURIComponent(arguments[c]);
			return "Minified React error #" + a + "; visit " + b + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
		}
		var p = Object.prototype.hasOwnProperty;
		var fa = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/;
		var ha = {};
		var ia = {};
		function ja(a) {
			if (p.call(ia, a)) return !0;
			if (p.call(ha, a)) return !1;
			if (fa.test(a)) return ia[a] = !0;
			ha[a] = !0;
			return !1;
		}
		function r(a, b, c, d, f, e, g) {
			this.acceptsBooleans = 2 === b || 3 === b || 4 === b;
			this.attributeName = d;
			this.attributeNamespace = f;
			this.mustUseProperty = c;
			this.propertyName = a;
			this.type = b;
			this.sanitizeURL = e;
			this.removeEmptyString = g;
		}
		var t = {};
		"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(a) {
			t[a] = new r(a, 0, !1, a, null, !1, !1);
		});
		[
			["acceptCharset", "accept-charset"],
			["className", "class"],
			["htmlFor", "for"],
			["httpEquiv", "http-equiv"]
		].forEach(function(a) {
			var b = a[0];
			t[b] = new r(b, 1, !1, a[1], null, !1, !1);
		});
		[
			"contentEditable",
			"draggable",
			"spellCheck",
			"value"
		].forEach(function(a) {
			t[a] = new r(a, 2, !1, a.toLowerCase(), null, !1, !1);
		});
		[
			"autoReverse",
			"externalResourcesRequired",
			"focusable",
			"preserveAlpha"
		].forEach(function(a) {
			t[a] = new r(a, 2, !1, a, null, !1, !1);
		});
		"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(a) {
			t[a] = new r(a, 3, !1, a.toLowerCase(), null, !1, !1);
		});
		[
			"checked",
			"multiple",
			"muted",
			"selected"
		].forEach(function(a) {
			t[a] = new r(a, 3, !0, a, null, !1, !1);
		});
		["capture", "download"].forEach(function(a) {
			t[a] = new r(a, 4, !1, a, null, !1, !1);
		});
		[
			"cols",
			"rows",
			"size",
			"span"
		].forEach(function(a) {
			t[a] = new r(a, 6, !1, a, null, !1, !1);
		});
		["rowSpan", "start"].forEach(function(a) {
			t[a] = new r(a, 5, !1, a.toLowerCase(), null, !1, !1);
		});
		var ka = /[\-:]([a-z])/g;
		function la(a) {
			return a[1].toUpperCase();
		}
		"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(a) {
			var b = a.replace(ka, la);
			t[b] = new r(b, 1, !1, a, null, !1, !1);
		});
		"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(a) {
			var b = a.replace(ka, la);
			t[b] = new r(b, 1, !1, a, "http://www.w3.org/1999/xlink", !1, !1);
		});
		[
			"xml:base",
			"xml:lang",
			"xml:space"
		].forEach(function(a) {
			var b = a.replace(ka, la);
			t[b] = new r(b, 1, !1, a, "http://www.w3.org/XML/1998/namespace", !1, !1);
		});
		["tabIndex", "crossOrigin"].forEach(function(a) {
			t[a] = new r(a, 1, !1, a.toLowerCase(), null, !1, !1);
		});
		t.xlinkHref = new r("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
		[
			"src",
			"href",
			"action",
			"formAction"
		].forEach(function(a) {
			t[a] = new r(a, 1, !1, a.toLowerCase(), null, !0, !0);
		});
		var u = {
			animationIterationCount: !0,
			aspectRatio: !0,
			borderImageOutset: !0,
			borderImageSlice: !0,
			borderImageWidth: !0,
			boxFlex: !0,
			boxFlexGroup: !0,
			boxOrdinalGroup: !0,
			columnCount: !0,
			columns: !0,
			flex: !0,
			flexGrow: !0,
			flexPositive: !0,
			flexShrink: !0,
			flexNegative: !0,
			flexOrder: !0,
			gridArea: !0,
			gridRow: !0,
			gridRowEnd: !0,
			gridRowSpan: !0,
			gridRowStart: !0,
			gridColumn: !0,
			gridColumnEnd: !0,
			gridColumnSpan: !0,
			gridColumnStart: !0,
			fontWeight: !0,
			lineClamp: !0,
			lineHeight: !0,
			opacity: !0,
			order: !0,
			orphans: !0,
			tabSize: !0,
			widows: !0,
			zIndex: !0,
			zoom: !0,
			fillOpacity: !0,
			floodOpacity: !0,
			stopOpacity: !0,
			strokeDasharray: !0,
			strokeDashoffset: !0,
			strokeMiterlimit: !0,
			strokeOpacity: !0,
			strokeWidth: !0
		};
		var ma = [
			"Webkit",
			"ms",
			"Moz",
			"O"
		];
		Object.keys(u).forEach(function(a) {
			ma.forEach(function(b) {
				b = b + a.charAt(0).toUpperCase() + a.substring(1);
				u[b] = u[a];
			});
		});
		var na = /["'&<>]/;
		function v(a) {
			if ("boolean" === typeof a || "number" === typeof a) return "" + a;
			a = "" + a;
			var b = na.exec(a);
			if (b) {
				var c = "", d, f = 0;
				for (d = b.index; d < a.length; d++) {
					switch (a.charCodeAt(d)) {
						case 34:
							b = "&quot;";
							break;
						case 38:
							b = "&amp;";
							break;
						case 39:
							b = "&#x27;";
							break;
						case 60:
							b = "&lt;";
							break;
						case 62:
							b = "&gt;";
							break;
						default: continue;
					}
					f !== d && (c += a.substring(f, d));
					f = d + 1;
					c += b;
				}
				a = f !== d ? c + a.substring(f, d) : c;
			}
			return a;
		}
		var oa = /([A-Z])/g;
		var pa = /^ms-/;
		var qa = Array.isArray;
		function w(a, b) {
			return {
				insertionMode: a,
				selectedValue: b
			};
		}
		function ra(a, b, c) {
			switch (b) {
				case "select": return w(1, null != c.value ? c.value : c.defaultValue);
				case "svg": return w(2, null);
				case "math": return w(3, null);
				case "foreignObject": return w(1, null);
				case "table": return w(4, null);
				case "thead":
				case "tbody":
				case "tfoot": return w(5, null);
				case "colgroup": return w(7, null);
				case "tr": return w(6, null);
			}
			return 4 <= a.insertionMode || 0 === a.insertionMode ? w(1, null) : a;
		}
		var sa = /* @__PURE__ */ new Map();
		function ta(a, b, c) {
			if ("object" !== typeof c) throw Error(l(62));
			b = !0;
			for (var d in c) if (p.call(c, d)) {
				var f = c[d];
				if (null != f && "boolean" !== typeof f && "" !== f) {
					if (0 === d.indexOf("--")) {
						var e = v(d);
						f = v(("" + f).trim());
					} else {
						e = d;
						var g = sa.get(e);
						void 0 !== g ? e = g : (g = v(e.replace(oa, "-$1").toLowerCase().replace(pa, "-ms-")), sa.set(e, g), e = g);
						f = "number" === typeof f ? 0 === f || p.call(u, d) ? "" + f : f + "px" : v(("" + f).trim());
					}
					b ? (b = !1, a.push(" style=\"", e, ":", f)) : a.push(";", e, ":", f);
				}
			}
			b || a.push("\"");
		}
		function x(a, b, c, d) {
			switch (c) {
				case "style":
					ta(a, b, d);
					return;
				case "defaultValue":
				case "defaultChecked":
				case "innerHTML":
				case "suppressContentEditableWarning":
				case "suppressHydrationWarning": return;
			}
			if (!(2 < c.length) || "o" !== c[0] && "O" !== c[0] || "n" !== c[1] && "N" !== c[1]) {
				if (b = t.hasOwnProperty(c) ? t[c] : null, null !== b) {
					switch (typeof d) {
						case "function":
						case "symbol": return;
						case "boolean": if (!b.acceptsBooleans) return;
					}
					c = b.attributeName;
					switch (b.type) {
						case 3:
							d && a.push(" ", c, "=\"\"");
							break;
						case 4:
							!0 === d ? a.push(" ", c, "=\"\"") : !1 !== d && a.push(" ", c, "=\"", v(d), "\"");
							break;
						case 5:
							isNaN(d) || a.push(" ", c, "=\"", v(d), "\"");
							break;
						case 6:
							!isNaN(d) && 1 <= d && a.push(" ", c, "=\"", v(d), "\"");
							break;
						default: b.sanitizeURL && (d = "" + d), a.push(" ", c, "=\"", v(d), "\"");
					}
				} else if (ja(c)) {
					switch (typeof d) {
						case "function":
						case "symbol": return;
						case "boolean": if (b = c.toLowerCase().slice(0, 5), "data-" !== b && "aria-" !== b) return;
					}
					a.push(" ", c, "=\"", v(d), "\"");
				}
			}
		}
		function y(a, b, c) {
			if (null != b) {
				if (null != c) throw Error(l(60));
				if ("object" !== typeof b || !("__html" in b)) throw Error(l(61));
				b = b.__html;
				null !== b && void 0 !== b && a.push("" + b);
			}
		}
		function ua(a) {
			var b = "";
			aa.Children.forEach(a, function(a) {
				null != a && (b += a);
			});
			return b;
		}
		function va(a, b, c, d) {
			a.push(A(c));
			var f = c = null, e;
			for (e in b) if (p.call(b, e)) {
				var g = b[e];
				if (null != g) switch (e) {
					case "children":
						c = g;
						break;
					case "dangerouslySetInnerHTML":
						f = g;
						break;
					default: x(a, d, e, g);
				}
			}
			a.push(">");
			y(a, f, c);
			return "string" === typeof c ? (a.push(v(c)), null) : c;
		}
		var wa = /^[a-zA-Z][a-zA-Z:_\.\-\d]*$/;
		var xa = /* @__PURE__ */ new Map();
		function A(a) {
			var b = xa.get(a);
			if (void 0 === b) {
				if (!wa.test(a)) throw Error(l(65, a));
				b = "<" + a;
				xa.set(a, b);
			}
			return b;
		}
		function ya(a, b, c, d, f) {
			switch (b) {
				case "select":
					a.push(A("select"));
					var e = null, g = null;
					for (n in c) if (p.call(c, n)) {
						var h = c[n];
						if (null != h) switch (n) {
							case "children":
								e = h;
								break;
							case "dangerouslySetInnerHTML":
								g = h;
								break;
							case "defaultValue":
							case "value": break;
							default: x(a, d, n, h);
						}
					}
					a.push(">");
					y(a, g, e);
					return e;
				case "option":
					g = f.selectedValue;
					a.push(A("option"));
					var k = h = null, m = null;
					var n = null;
					for (e in c) if (p.call(c, e)) {
						var q = c[e];
						if (null != q) switch (e) {
							case "children":
								h = q;
								break;
							case "selected":
								m = q;
								break;
							case "dangerouslySetInnerHTML":
								n = q;
								break;
							case "value": k = q;
							default: x(a, d, e, q);
						}
					}
					if (null != g) if (c = null !== k ? "" + k : ua(h), qa(g)) {
						for (d = 0; d < g.length; d++) if ("" + g[d] === c) {
							a.push(" selected=\"\"");
							break;
						}
					} else "" + g === c && a.push(" selected=\"\"");
					else m && a.push(" selected=\"\"");
					a.push(">");
					y(a, n, h);
					return h;
				case "textarea":
					a.push(A("textarea"));
					n = g = e = null;
					for (h in c) if (p.call(c, h) && (k = c[h], null != k)) switch (h) {
						case "children":
							n = k;
							break;
						case "value":
							e = k;
							break;
						case "defaultValue":
							g = k;
							break;
						case "dangerouslySetInnerHTML": throw Error(l(91));
						default: x(a, d, h, k);
					}
					null === e && null !== g && (e = g);
					a.push(">");
					if (null != n) {
						if (null != e) throw Error(l(92));
						if (qa(n) && 1 < n.length) throw Error(l(93));
						e = "" + n;
					}
					"string" === typeof e && "\n" === e[0] && a.push("\n");
					null !== e && a.push(v("" + e));
					return null;
				case "input":
					a.push(A("input"));
					k = n = h = e = null;
					for (g in c) if (p.call(c, g) && (m = c[g], null != m)) switch (g) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(l(399, "input"));
						case "defaultChecked":
							k = m;
							break;
						case "defaultValue":
							h = m;
							break;
						case "checked":
							n = m;
							break;
						case "value":
							e = m;
							break;
						default: x(a, d, g, m);
					}
					null !== n ? x(a, d, "checked", n) : null !== k && x(a, d, "checked", k);
					null !== e ? x(a, d, "value", e) : null !== h && x(a, d, "value", h);
					a.push("/>");
					return null;
				case "menuitem":
					a.push(A("menuitem"));
					for (var C in c) if (p.call(c, C) && (e = c[C], null != e)) switch (C) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(l(400));
						default: x(a, d, C, e);
					}
					a.push(">");
					return null;
				case "title":
					a.push(A("title"));
					e = null;
					for (q in c) if (p.call(c, q) && (g = c[q], null != g)) switch (q) {
						case "children":
							e = g;
							break;
						case "dangerouslySetInnerHTML": throw Error(l(434));
						default: x(a, d, q, g);
					}
					a.push(">");
					return e;
				case "listing":
				case "pre":
					a.push(A(b));
					g = e = null;
					for (k in c) if (p.call(c, k) && (h = c[k], null != h)) switch (k) {
						case "children":
							e = h;
							break;
						case "dangerouslySetInnerHTML":
							g = h;
							break;
						default: x(a, d, k, h);
					}
					a.push(">");
					if (null != g) {
						if (null != e) throw Error(l(60));
						if ("object" !== typeof g || !("__html" in g)) throw Error(l(61));
						c = g.__html;
						null !== c && void 0 !== c && ("string" === typeof c && 0 < c.length && "\n" === c[0] ? a.push("\n", c) : a.push("" + c));
					}
					"string" === typeof e && "\n" === e[0] && a.push("\n");
					return e;
				case "area":
				case "base":
				case "br":
				case "col":
				case "embed":
				case "hr":
				case "img":
				case "keygen":
				case "link":
				case "meta":
				case "param":
				case "source":
				case "track":
				case "wbr":
					a.push(A(b));
					for (var D in c) if (p.call(c, D) && (e = c[D], null != e)) switch (D) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(l(399, b));
						default: x(a, d, D, e);
					}
					a.push("/>");
					return null;
				case "annotation-xml":
				case "color-profile":
				case "font-face":
				case "font-face-src":
				case "font-face-uri":
				case "font-face-format":
				case "font-face-name":
				case "missing-glyph": return va(a, c, b, d);
				case "html": return 0 === f.insertionMode && a.push("<!DOCTYPE html>"), va(a, c, b, d);
				default:
					if (-1 === b.indexOf("-") && "string" !== typeof c.is) return va(a, c, b, d);
					a.push(A(b));
					g = e = null;
					for (m in c) if (p.call(c, m) && (h = c[m], null != h)) switch (m) {
						case "children":
							e = h;
							break;
						case "dangerouslySetInnerHTML":
							g = h;
							break;
						case "style":
							ta(a, d, h);
							break;
						case "suppressContentEditableWarning":
						case "suppressHydrationWarning": break;
						default: ja(m) && "function" !== typeof h && "symbol" !== typeof h && a.push(" ", m, "=\"", v(h), "\"");
					}
					a.push(">");
					y(a, g, e);
					return e;
			}
		}
		function za(a, b, c) {
			a.push("<!--$?--><template id=\"");
			if (null === c) throw Error(l(395));
			a.push(c);
			return a.push("\"></template>");
		}
		function Aa(a, b, c, d) {
			switch (c.insertionMode) {
				case 0:
				case 1: return a.push("<div hidden id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 2: return a.push("<svg aria-hidden=\"true\" style=\"display:none\" id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 3: return a.push("<math aria-hidden=\"true\" style=\"display:none\" id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 4: return a.push("<table hidden id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 5: return a.push("<table hidden><tbody id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 6: return a.push("<table hidden><tr id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				case 7: return a.push("<table hidden><colgroup id=\""), a.push(b.segmentPrefix), b = d.toString(16), a.push(b), a.push("\">");
				default: throw Error(l(397));
			}
		}
		function Ba(a, b) {
			switch (b.insertionMode) {
				case 0:
				case 1: return a.push("</div>");
				case 2: return a.push("</svg>");
				case 3: return a.push("</math>");
				case 4: return a.push("</table>");
				case 5: return a.push("</tbody></table>");
				case 6: return a.push("</tr></table>");
				case 7: return a.push("</colgroup></table>");
				default: throw Error(l(397));
			}
		}
		var Ca = /[<\u2028\u2029]/g;
		function Da(a) {
			return JSON.stringify(a).replace(Ca, function(a) {
				switch (a) {
					case "<": return "\\u003c";
					case "\u2028": return "\\u2028";
					case "\u2029": return "\\u2029";
					default: throw Error("escapeJSStringsForInstructionScripts encountered a match it does not know how to replace. this means the match regex and the replacement characters are no longer in sync. This is a bug in React");
				}
			});
		}
		function Ea(a, b) {
			b = void 0 === b ? "" : b;
			return {
				bootstrapChunks: [],
				startInlineScript: "<script>",
				placeholderPrefix: b + "P:",
				segmentPrefix: b + "S:",
				boundaryPrefix: b + "B:",
				idPrefix: b,
				nextSuspenseID: 0,
				sentCompleteSegmentFunction: !1,
				sentCompleteBoundaryFunction: !1,
				sentClientRenderFunction: !1,
				generateStaticMarkup: a
			};
		}
		function Fa(a, b, c, d) {
			if (c.generateStaticMarkup) return a.push(v(b)), !1;
			"" === b ? a = d : (d && a.push("<!-- -->"), a.push(v(b)), a = !0);
			return a;
		}
		var B = Object.assign;
		var Ga = Symbol.for("react.element");
		var Ha = Symbol.for("react.portal");
		var Ia = Symbol.for("react.fragment");
		var Ja = Symbol.for("react.strict_mode");
		var Ka = Symbol.for("react.profiler");
		var La = Symbol.for("react.provider");
		var Ma = Symbol.for("react.context");
		var Na = Symbol.for("react.forward_ref");
		var Oa = Symbol.for("react.suspense");
		var Pa = Symbol.for("react.suspense_list");
		var Qa = Symbol.for("react.memo");
		var Ra = Symbol.for("react.lazy");
		var Sa = Symbol.for("react.scope");
		var Ta = Symbol.for("react.debug_trace_mode");
		var Ua = Symbol.for("react.legacy_hidden");
		var Va = Symbol.for("react.default_value");
		var Wa = Symbol.iterator;
		function Xa(a) {
			if (null == a) return null;
			if ("function" === typeof a) return a.displayName || a.name || null;
			if ("string" === typeof a) return a;
			switch (a) {
				case Ia: return "Fragment";
				case Ha: return "Portal";
				case Ka: return "Profiler";
				case Ja: return "StrictMode";
				case Oa: return "Suspense";
				case Pa: return "SuspenseList";
			}
			if ("object" === typeof a) switch (a.$$typeof) {
				case Ma: return (a.displayName || "Context") + ".Consumer";
				case La: return (a._context.displayName || "Context") + ".Provider";
				case Na:
					var b = a.render;
					a = a.displayName;
					a || (a = b.displayName || b.name || "", a = "" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
					return a;
				case Qa: return b = a.displayName || null, null !== b ? b : Xa(a.type) || "Memo";
				case Ra:
					b = a._payload;
					a = a._init;
					try {
						return Xa(a(b));
					} catch (c) {}
			}
			return null;
		}
		var Ya = {};
		function Za(a, b) {
			a = a.contextTypes;
			if (!a) return Ya;
			var c = {}, d;
			for (d in a) c[d] = b[d];
			return c;
		}
		var E = null;
		function F(a, b) {
			if (a !== b) {
				a.context._currentValue2 = a.parentValue;
				a = a.parent;
				var c = b.parent;
				if (null === a) {
					if (null !== c) throw Error(l(401));
				} else {
					if (null === c) throw Error(l(401));
					F(a, c);
				}
				b.context._currentValue2 = b.value;
			}
		}
		function $a(a) {
			a.context._currentValue2 = a.parentValue;
			a = a.parent;
			null !== a && $a(a);
		}
		function ab(a) {
			var b = a.parent;
			null !== b && ab(b);
			a.context._currentValue2 = a.value;
		}
		function bb(a, b) {
			a.context._currentValue2 = a.parentValue;
			a = a.parent;
			if (null === a) throw Error(l(402));
			a.depth === b.depth ? F(a, b) : bb(a, b);
		}
		function cb(a, b) {
			var c = b.parent;
			if (null === c) throw Error(l(402));
			a.depth === c.depth ? F(a, c) : cb(a, c);
			b.context._currentValue2 = b.value;
		}
		function G(a) {
			var b = E;
			b !== a && (null === b ? ab(a) : null === a ? $a(b) : b.depth === a.depth ? F(b, a) : b.depth > a.depth ? bb(b, a) : cb(b, a), E = a);
		}
		var db = {
			isMounted: function() {
				return !1;
			},
			enqueueSetState: function(a, b) {
				a = a._reactInternals;
				null !== a.queue && a.queue.push(b);
			},
			enqueueReplaceState: function(a, b) {
				a = a._reactInternals;
				a.replace = !0;
				a.queue = [b];
			},
			enqueueForceUpdate: function() {}
		};
		function eb(a, b, c, d) {
			var f = void 0 !== a.state ? a.state : null;
			a.updater = db;
			a.props = c;
			a.state = f;
			var e = {
				queue: [],
				replace: !1
			};
			a._reactInternals = e;
			var g = b.contextType;
			a.context = "object" === typeof g && null !== g ? g._currentValue2 : d;
			g = b.getDerivedStateFromProps;
			"function" === typeof g && (g = g(c, f), f = null === g || void 0 === g ? f : B({}, f, g), a.state = f);
			if ("function" !== typeof b.getDerivedStateFromProps && "function" !== typeof a.getSnapshotBeforeUpdate && ("function" === typeof a.UNSAFE_componentWillMount || "function" === typeof a.componentWillMount)) if (b = a.state, "function" === typeof a.componentWillMount && a.componentWillMount(), "function" === typeof a.UNSAFE_componentWillMount && a.UNSAFE_componentWillMount(), b !== a.state && db.enqueueReplaceState(a, a.state, null), null !== e.queue && 0 < e.queue.length) if (b = e.queue, g = e.replace, e.queue = null, e.replace = !1, g && 1 === b.length) a.state = b[0];
			else {
				e = g ? b[0] : a.state;
				f = !0;
				for (g = g ? 1 : 0; g < b.length; g++) {
					var h = b[g];
					h = "function" === typeof h ? h.call(a, e, c, d) : h;
					null != h && (f ? (f = !1, e = B({}, e, h)) : B(e, h));
				}
				a.state = e;
			}
			else e.queue = null;
		}
		var fb = {
			id: 1,
			overflow: ""
		};
		function gb(a, b, c) {
			var d = a.id;
			a = a.overflow;
			var f = 32 - H(d) - 1;
			d &= ~(1 << f);
			c += 1;
			var e = 32 - H(b) + f;
			if (30 < e) {
				var g = f - f % 5;
				e = (d & (1 << g) - 1).toString(32);
				d >>= g;
				f -= g;
				return {
					id: 1 << 32 - H(b) + f | c << f | d,
					overflow: e + a
				};
			}
			return {
				id: 1 << e | c << f | d,
				overflow: a
			};
		}
		var H = Math.clz32 ? Math.clz32 : hb;
		var ib = Math.log;
		var jb = Math.LN2;
		function hb(a) {
			a >>>= 0;
			return 0 === a ? 32 : 31 - (ib(a) / jb | 0) | 0;
		}
		function kb(a, b) {
			return a === b && (0 !== a || 1 / a === 1 / b) || a !== a && b !== b;
		}
		var lb = "function" === typeof Object.is ? Object.is : kb;
		var I = null;
		var ob = null;
		var J = null;
		var K = null;
		var L = !1;
		var M = !1;
		var N = 0;
		var O = null;
		var P = 0;
		function Q() {
			if (null === I) throw Error(l(321));
			return I;
		}
		function pb() {
			if (0 < P) throw Error(l(312));
			return {
				memoizedState: null,
				queue: null,
				next: null
			};
		}
		function qb() {
			null === K ? null === J ? (L = !1, J = K = pb()) : (L = !0, K = J) : null === K.next ? (L = !1, K = K.next = pb()) : (L = !0, K = K.next);
			return K;
		}
		function rb() {
			ob = I = null;
			M = !1;
			J = null;
			P = 0;
			K = O = null;
		}
		function sb(a, b) {
			return "function" === typeof b ? b(a) : b;
		}
		function tb(a, b, c) {
			I = Q();
			K = qb();
			if (L) {
				var d = K.queue;
				b = d.dispatch;
				if (null !== O && (c = O.get(d), void 0 !== c)) {
					O.delete(d);
					d = K.memoizedState;
					do
						d = a(d, c.action), c = c.next;
					while (null !== c);
					K.memoizedState = d;
					return [d, b];
				}
				return [K.memoizedState, b];
			}
			a = a === sb ? "function" === typeof b ? b() : b : void 0 !== c ? c(b) : b;
			K.memoizedState = a;
			a = K.queue = {
				last: null,
				dispatch: null
			};
			a = a.dispatch = ub.bind(null, I, a);
			return [K.memoizedState, a];
		}
		function vb(a, b) {
			I = Q();
			K = qb();
			b = void 0 === b ? null : b;
			if (null !== K) {
				var c = K.memoizedState;
				if (null !== c && null !== b) {
					var d = c[1];
					a: if (null === d) d = !1;
					else {
						for (var f = 0; f < d.length && f < b.length; f++) if (!lb(b[f], d[f])) {
							d = !1;
							break a;
						}
						d = !0;
					}
					if (d) return c[0];
				}
			}
			a = a();
			K.memoizedState = [a, b];
			return a;
		}
		function ub(a, b, c) {
			if (25 <= P) throw Error(l(301));
			if (a === I) if (M = !0, a = {
				action: c,
				next: null
			}, null === O && (O = /* @__PURE__ */ new Map()), c = O.get(b), void 0 === c) O.set(b, a);
			else {
				for (b = c; null !== b.next;) b = b.next;
				b.next = a;
			}
		}
		function wb() {
			throw Error(l(394));
		}
		function R() {}
		var xb = {
			readContext: function(a) {
				return a._currentValue2;
			},
			useContext: function(a) {
				Q();
				return a._currentValue2;
			},
			useMemo: vb,
			useReducer: tb,
			useRef: function(a) {
				I = Q();
				K = qb();
				var b = K.memoizedState;
				return null === b ? (a = { current: a }, K.memoizedState = a) : b;
			},
			useState: function(a) {
				return tb(sb, a);
			},
			useInsertionEffect: R,
			useLayoutEffect: function() {},
			useCallback: function(a, b) {
				return vb(function() {
					return a;
				}, b);
			},
			useImperativeHandle: R,
			useEffect: R,
			useDebugValue: R,
			useDeferredValue: function(a) {
				Q();
				return a;
			},
			useTransition: function() {
				Q();
				return [!1, wb];
			},
			useId: function() {
				var a = ob.treeContext;
				var b = a.overflow;
				a = a.id;
				a = (a & ~(1 << 32 - H(a) - 1)).toString(32) + b;
				var c = S;
				if (null === c) throw Error(l(404));
				b = N++;
				a = ":" + c.idPrefix + "R" + a;
				0 < b && (a += "H" + b.toString(32));
				return a + ":";
			},
			useMutableSource: function(a, b) {
				Q();
				return b(a._source);
			},
			useSyncExternalStore: function(a, b, c) {
				if (void 0 === c) throw Error(l(407));
				return c();
			}
		};
		var S = null;
		var yb = aa.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
		function zb(a) {
			console.error(a);
			return null;
		}
		function T() {}
		function Ab(a, b, c, d, f, e, g, h, k) {
			var m = [], n = /* @__PURE__ */ new Set();
			b = {
				destination: null,
				responseState: b,
				progressiveChunkSize: void 0 === d ? 12800 : d,
				status: 0,
				fatalError: null,
				nextSegmentId: 0,
				allPendingTasks: 0,
				pendingRootTasks: 0,
				completedRootSegment: null,
				abortableTasks: n,
				pingedTasks: m,
				clientRenderedBoundaries: [],
				completedBoundaries: [],
				partialBoundaries: [],
				onError: void 0 === f ? zb : f,
				onAllReady: void 0 === e ? T : e,
				onShellReady: void 0 === g ? T : g,
				onShellError: void 0 === h ? T : h,
				onFatalError: void 0 === k ? T : k
			};
			c = U(b, 0, null, c, !1, !1);
			c.parentFlushed = !0;
			a = Bb(b, a, null, c, n, Ya, null, fb);
			m.push(a);
			return b;
		}
		function Bb(a, b, c, d, f, e, g, h) {
			a.allPendingTasks++;
			null === c ? a.pendingRootTasks++ : c.pendingTasks++;
			var k = {
				node: b,
				ping: function() {
					var b = a.pingedTasks;
					b.push(k);
					1 === b.length && Cb(a);
				},
				blockedBoundary: c,
				blockedSegment: d,
				abortSet: f,
				legacyContext: e,
				context: g,
				treeContext: h
			};
			f.add(k);
			return k;
		}
		function U(a, b, c, d, f, e) {
			return {
				status: 0,
				id: -1,
				index: b,
				parentFlushed: !1,
				chunks: [],
				children: [],
				formatContext: d,
				boundary: c,
				lastPushedText: f,
				textEmbedded: e
			};
		}
		function V(a, b) {
			a = a.onError(b);
			if (null != a && "string" !== typeof a) throw Error("onError returned something with a type other than \"string\". onError should return a string and may return null or undefined but must not return anything else. It received something of type \"" + typeof a + "\" instead");
			return a;
		}
		function W(a, b) {
			var c = a.onShellError;
			c(b);
			c = a.onFatalError;
			c(b);
			null !== a.destination ? (a.status = 2, a.destination.destroy(b)) : (a.status = 1, a.fatalError = b);
		}
		function Db(a, b, c, d, f) {
			I = {};
			ob = b;
			N = 0;
			for (a = c(d, f); M;) M = !1, N = 0, P += 1, K = null, a = c(d, f);
			rb();
			return a;
		}
		function Eb(a, b, c, d) {
			var f = c.render(), e = d.childContextTypes;
			if (null !== e && void 0 !== e) {
				var g = b.legacyContext;
				if ("function" !== typeof c.getChildContext) d = g;
				else {
					c = c.getChildContext();
					for (var h in c) if (!(h in e)) throw Error(l(108, Xa(d) || "Unknown", h));
					d = B({}, g, c);
				}
				b.legacyContext = d;
				X(a, b, f);
				b.legacyContext = g;
			} else X(a, b, f);
		}
		function Fb(a, b) {
			if (a && a.defaultProps) {
				b = B({}, b);
				a = a.defaultProps;
				for (var c in a) void 0 === b[c] && (b[c] = a[c]);
				return b;
			}
			return b;
		}
		function Gb(a, b, c, d, f) {
			if ("function" === typeof c) if (c.prototype && c.prototype.isReactComponent) {
				f = Za(c, b.legacyContext);
				var e = c.contextType;
				e = new c(d, "object" === typeof e && null !== e ? e._currentValue2 : f);
				eb(e, c, d, f);
				Eb(a, b, e, c);
			} else {
				e = Za(c, b.legacyContext);
				f = Db(a, b, c, d, e);
				var g = 0 !== N;
				if ("object" === typeof f && null !== f && "function" === typeof f.render && void 0 === f.$$typeof) eb(f, c, d, e), Eb(a, b, f, c);
				else if (g) {
					d = b.treeContext;
					b.treeContext = gb(d, 1, 0);
					try {
						X(a, b, f);
					} finally {
						b.treeContext = d;
					}
				} else X(a, b, f);
			}
			else if ("string" === typeof c) {
				f = b.blockedSegment;
				e = ya(f.chunks, c, d, a.responseState, f.formatContext);
				f.lastPushedText = !1;
				g = f.formatContext;
				f.formatContext = ra(g, c, d);
				Hb(a, b, e);
				f.formatContext = g;
				switch (c) {
					case "area":
					case "base":
					case "br":
					case "col":
					case "embed":
					case "hr":
					case "img":
					case "input":
					case "keygen":
					case "link":
					case "meta":
					case "param":
					case "source":
					case "track":
					case "wbr": break;
					default: f.chunks.push("</", c, ">");
				}
				f.lastPushedText = !1;
			} else {
				switch (c) {
					case Ua:
					case Ta:
					case Ja:
					case Ka:
					case Ia:
						X(a, b, d.children);
						return;
					case Pa:
						X(a, b, d.children);
						return;
					case Sa: throw Error(l(343));
					case Oa:
						a: {
							c = b.blockedBoundary;
							f = b.blockedSegment;
							e = d.fallback;
							d = d.children;
							g = /* @__PURE__ */ new Set();
							var h = {
								id: null,
								rootSegmentID: -1,
								parentFlushed: !1,
								pendingTasks: 0,
								forceClientRender: !1,
								completedSegments: [],
								byteSize: 0,
								fallbackAbortableTasks: g,
								errorDigest: null
							}, k = U(a, f.chunks.length, h, f.formatContext, !1, !1);
							f.children.push(k);
							f.lastPushedText = !1;
							var m = U(a, 0, null, f.formatContext, !1, !1);
							m.parentFlushed = !0;
							b.blockedBoundary = h;
							b.blockedSegment = m;
							try {
								if (Hb(a, b, d), a.responseState.generateStaticMarkup || m.lastPushedText && m.textEmbedded && m.chunks.push("<!-- -->"), m.status = 1, Y(h, m), 0 === h.pendingTasks) break a;
							} catch (n) {
								m.status = 4, h.forceClientRender = !0, h.errorDigest = V(a, n);
							} finally {
								b.blockedBoundary = c, b.blockedSegment = f;
							}
							b = Bb(a, e, c, k, g, b.legacyContext, b.context, b.treeContext);
							a.pingedTasks.push(b);
						}
						return;
				}
				if ("object" === typeof c && null !== c) switch (c.$$typeof) {
					case Na:
						d = Db(a, b, c.render, d, f);
						if (0 !== N) {
							c = b.treeContext;
							b.treeContext = gb(c, 1, 0);
							try {
								X(a, b, d);
							} finally {
								b.treeContext = c;
							}
						} else X(a, b, d);
						return;
					case Qa:
						c = c.type;
						d = Fb(c, d);
						Gb(a, b, c, d, f);
						return;
					case La:
						f = d.children;
						c = c._context;
						d = d.value;
						e = c._currentValue2;
						c._currentValue2 = d;
						g = E;
						E = d = {
							parent: g,
							depth: null === g ? 0 : g.depth + 1,
							context: c,
							parentValue: e,
							value: d
						};
						b.context = d;
						X(a, b, f);
						a = E;
						if (null === a) throw Error(l(403));
						d = a.parentValue;
						a.context._currentValue2 = d === Va ? a.context._defaultValue : d;
						a = E = a.parent;
						b.context = a;
						return;
					case Ma:
						d = d.children;
						d = d(c._currentValue2);
						X(a, b, d);
						return;
					case Ra:
						f = c._init;
						c = f(c._payload);
						d = Fb(c, d);
						Gb(a, b, c, d, void 0);
						return;
				}
				throw Error(l(130, null == c ? c : typeof c, ""));
			}
		}
		function X(a, b, c) {
			b.node = c;
			if ("object" === typeof c && null !== c) {
				switch (c.$$typeof) {
					case Ga:
						Gb(a, b, c.type, c.props, c.ref);
						return;
					case Ha: throw Error(l(257));
					case Ra:
						var d = c._init;
						c = d(c._payload);
						X(a, b, c);
						return;
				}
				if (qa(c)) {
					Ib(a, b, c);
					return;
				}
				null === c || "object" !== typeof c ? d = null : (d = Wa && c[Wa] || c["@@iterator"], d = "function" === typeof d ? d : null);
				if (d && (d = d.call(c))) {
					c = d.next();
					if (!c.done) {
						var f = [];
						do
							f.push(c.value), c = d.next();
						while (!c.done);
						Ib(a, b, f);
					}
					return;
				}
				a = Object.prototype.toString.call(c);
				throw Error(l(31, "[object Object]" === a ? "object with keys {" + Object.keys(c).join(", ") + "}" : a));
			}
			"string" === typeof c ? (d = b.blockedSegment, d.lastPushedText = Fa(b.blockedSegment.chunks, c, a.responseState, d.lastPushedText)) : "number" === typeof c && (d = b.blockedSegment, d.lastPushedText = Fa(b.blockedSegment.chunks, "" + c, a.responseState, d.lastPushedText));
		}
		function Ib(a, b, c) {
			for (var d = c.length, f = 0; f < d; f++) {
				var e = b.treeContext;
				b.treeContext = gb(e, d, f);
				try {
					Hb(a, b, c[f]);
				} finally {
					b.treeContext = e;
				}
			}
		}
		function Hb(a, b, c) {
			var d = b.blockedSegment.formatContext, f = b.legacyContext, e = b.context;
			try {
				return X(a, b, c);
			} catch (k) {
				if (rb(), "object" === typeof k && null !== k && "function" === typeof k.then) {
					c = k;
					var g = b.blockedSegment, h = U(a, g.chunks.length, null, g.formatContext, g.lastPushedText, !0);
					g.children.push(h);
					g.lastPushedText = !1;
					a = Bb(a, b.node, b.blockedBoundary, h, b.abortSet, b.legacyContext, b.context, b.treeContext).ping;
					c.then(a, a);
					b.blockedSegment.formatContext = d;
					b.legacyContext = f;
					b.context = e;
					G(e);
				} else throw b.blockedSegment.formatContext = d, b.legacyContext = f, b.context = e, G(e), k;
			}
		}
		function Jb(a) {
			var b = a.blockedBoundary;
			a = a.blockedSegment;
			a.status = 3;
			Kb(this, b, a);
		}
		function Lb(a, b, c) {
			var d = a.blockedBoundary;
			a.blockedSegment.status = 3;
			null === d ? (b.allPendingTasks--, 2 !== b.status && (b.status = 2, null !== b.destination && b.destination.push(null))) : (d.pendingTasks--, d.forceClientRender || (d.forceClientRender = !0, a = void 0 === c ? Error(l(432)) : c, d.errorDigest = b.onError(a), d.parentFlushed && b.clientRenderedBoundaries.push(d)), d.fallbackAbortableTasks.forEach(function(a) {
				return Lb(a, b, c);
			}), d.fallbackAbortableTasks.clear(), b.allPendingTasks--, 0 === b.allPendingTasks && (d = b.onAllReady, d()));
		}
		function Y(a, b) {
			if (0 === b.chunks.length && 1 === b.children.length && null === b.children[0].boundary) {
				var c = b.children[0];
				c.id = b.id;
				c.parentFlushed = !0;
				1 === c.status && Y(a, c);
			} else a.completedSegments.push(b);
		}
		function Kb(a, b, c) {
			if (null === b) {
				if (c.parentFlushed) {
					if (null !== a.completedRootSegment) throw Error(l(389));
					a.completedRootSegment = c;
				}
				a.pendingRootTasks--;
				0 === a.pendingRootTasks && (a.onShellError = T, b = a.onShellReady, b());
			} else b.pendingTasks--, b.forceClientRender || (0 === b.pendingTasks ? (c.parentFlushed && 1 === c.status && Y(b, c), b.parentFlushed && a.completedBoundaries.push(b), b.fallbackAbortableTasks.forEach(Jb, a), b.fallbackAbortableTasks.clear()) : c.parentFlushed && 1 === c.status && (Y(b, c), 1 === b.completedSegments.length && b.parentFlushed && a.partialBoundaries.push(b)));
			a.allPendingTasks--;
			0 === a.allPendingTasks && (a = a.onAllReady, a());
		}
		function Cb(a) {
			if (2 !== a.status) {
				var b = E, c = yb.current;
				yb.current = xb;
				var d = S;
				S = a.responseState;
				try {
					var f = a.pingedTasks, e = 0;
					for (; e < f.length; e++) {
						var g = f[e];
						var h = a, k = g.blockedSegment;
						if (0 === k.status) {
							G(g.context);
							try {
								X(h, g, g.node), h.responseState.generateStaticMarkup || k.lastPushedText && k.textEmbedded && k.chunks.push("<!-- -->"), g.abortSet.delete(g), k.status = 1, Kb(h, g.blockedBoundary, k);
							} catch (z) {
								if (rb(), "object" === typeof z && null !== z && "function" === typeof z.then) {
									var m = g.ping;
									z.then(m, m);
								} else {
									g.abortSet.delete(g);
									k.status = 4;
									var n = g.blockedBoundary, q = z, C = V(h, q);
									null === n ? W(h, q) : (n.pendingTasks--, n.forceClientRender || (n.forceClientRender = !0, n.errorDigest = C, n.parentFlushed && h.clientRenderedBoundaries.push(n)));
									h.allPendingTasks--;
									if (0 === h.allPendingTasks) {
										var D = h.onAllReady;
										D();
									}
								}
							}
						}
					}
					f.splice(0, e);
					null !== a.destination && Mb(a, a.destination);
				} catch (z) {
					V(a, z), W(a, z);
				} finally {
					S = d, yb.current = c, c === xb && G(b);
				}
			}
		}
		function Z(a, b, c) {
			c.parentFlushed = !0;
			switch (c.status) {
				case 0:
					var d = c.id = a.nextSegmentId++;
					c.lastPushedText = !1;
					c.textEmbedded = !1;
					a = a.responseState;
					b.push("<template id=\"");
					b.push(a.placeholderPrefix);
					a = d.toString(16);
					b.push(a);
					return b.push("\"></template>");
				case 1:
					c.status = 2;
					var f = !0;
					d = c.chunks;
					var e = 0;
					c = c.children;
					for (var g = 0; g < c.length; g++) {
						for (f = c[g]; e < f.index; e++) b.push(d[e]);
						f = Nb(a, b, f);
					}
					for (; e < d.length - 1; e++) b.push(d[e]);
					e < d.length && (f = b.push(d[e]));
					return f;
				default: throw Error(l(390));
			}
		}
		function Nb(a, b, c) {
			var d = c.boundary;
			if (null === d) return Z(a, b, c);
			d.parentFlushed = !0;
			if (d.forceClientRender) return a.responseState.generateStaticMarkup || (d = d.errorDigest, b.push("<!--$!-->"), b.push("<template"), d && (b.push(" data-dgst=\""), d = v(d), b.push(d), b.push("\"")), b.push("></template>")), Z(a, b, c), a = a.responseState.generateStaticMarkup ? !0 : b.push("<!--/$-->"), a;
			if (0 < d.pendingTasks) {
				d.rootSegmentID = a.nextSegmentId++;
				0 < d.completedSegments.length && a.partialBoundaries.push(d);
				var f = a.responseState;
				var e = f.nextSuspenseID++;
				f = f.boundaryPrefix + e.toString(16);
				d = d.id = f;
				za(b, a.responseState, d);
				Z(a, b, c);
				return b.push("<!--/$-->");
			}
			if (d.byteSize > a.progressiveChunkSize) return d.rootSegmentID = a.nextSegmentId++, a.completedBoundaries.push(d), za(b, a.responseState, d.id), Z(a, b, c), b.push("<!--/$-->");
			a.responseState.generateStaticMarkup || b.push("<!--$-->");
			c = d.completedSegments;
			if (1 !== c.length) throw Error(l(391));
			Nb(a, b, c[0]);
			a = a.responseState.generateStaticMarkup ? !0 : b.push("<!--/$-->");
			return a;
		}
		function Ob(a, b, c) {
			Aa(b, a.responseState, c.formatContext, c.id);
			Nb(a, b, c);
			return Ba(b, c.formatContext);
		}
		function Pb(a, b, c) {
			for (var d = c.completedSegments, f = 0; f < d.length; f++) Qb(a, b, c, d[f]);
			d.length = 0;
			a = a.responseState;
			d = c.id;
			c = c.rootSegmentID;
			b.push(a.startInlineScript);
			a.sentCompleteBoundaryFunction ? b.push("$RC(\"") : (a.sentCompleteBoundaryFunction = !0, b.push("function $RC(a,b){a=document.getElementById(a);b=document.getElementById(b);b.parentNode.removeChild(b);if(a){a=a.previousSibling;var f=a.parentNode,c=a.nextSibling,e=0;do{if(c&&8===c.nodeType){var d=c.data;if(\"/$\"===d)if(0===e)break;else e--;else\"$\"!==d&&\"$?\"!==d&&\"$!\"!==d||e++}d=c.nextSibling;f.removeChild(c);c=d}while(c);for(;b.firstChild;)f.insertBefore(b.firstChild,c);a.data=\"$\";a._reactRetry&&a._reactRetry()}};$RC(\""));
			if (null === d) throw Error(l(395));
			c = c.toString(16);
			b.push(d);
			b.push("\",\"");
			b.push(a.segmentPrefix);
			b.push(c);
			return b.push("\")<\/script>");
		}
		function Qb(a, b, c, d) {
			if (2 === d.status) return !0;
			var f = d.id;
			if (-1 === f) {
				if (-1 === (d.id = c.rootSegmentID)) throw Error(l(392));
				return Ob(a, b, d);
			}
			Ob(a, b, d);
			a = a.responseState;
			b.push(a.startInlineScript);
			a.sentCompleteSegmentFunction ? b.push("$RS(\"") : (a.sentCompleteSegmentFunction = !0, b.push("function $RS(a,b){a=document.getElementById(a);b=document.getElementById(b);for(a.parentNode.removeChild(a);a.firstChild;)b.parentNode.insertBefore(a.firstChild,b);b.parentNode.removeChild(b)};$RS(\""));
			b.push(a.segmentPrefix);
			f = f.toString(16);
			b.push(f);
			b.push("\",\"");
			b.push(a.placeholderPrefix);
			b.push(f);
			return b.push("\")<\/script>");
		}
		function Mb(a, b) {
			try {
				var c = a.completedRootSegment;
				if (null !== c && 0 === a.pendingRootTasks) {
					Nb(a, b, c);
					a.completedRootSegment = null;
					var d = a.responseState.bootstrapChunks;
					for (c = 0; c < d.length - 1; c++) b.push(d[c]);
					c < d.length && b.push(d[c]);
				}
				var f = a.clientRenderedBoundaries, e = 0;
				for (; e < f.length; e++) {
					var g = f[e];
					d = b;
					var h = a.responseState, k = g.id, m = g.errorDigest, n = g.errorMessage, q = g.errorComponentStack;
					d.push(h.startInlineScript);
					h.sentClientRenderFunction ? d.push("$RX(\"") : (h.sentClientRenderFunction = !0, d.push("function $RX(b,c,d,e){var a=document.getElementById(b);a&&(b=a.previousSibling,b.data=\"$!\",a=a.dataset,c&&(a.dgst=c),d&&(a.msg=d),e&&(a.stck=e),b._reactRetry&&b._reactRetry())};$RX(\""));
					if (null === k) throw Error(l(395));
					d.push(k);
					d.push("\"");
					if (m || n || q) {
						d.push(",");
						var C = Da(m || "");
						d.push(C);
					}
					if (n || q) {
						d.push(",");
						var D = Da(n || "");
						d.push(D);
					}
					if (q) {
						d.push(",");
						var z = Da(q);
						d.push(z);
					}
					if (!d.push(")<\/script>")) {
						a.destination = null;
						e++;
						f.splice(0, e);
						return;
					}
				}
				f.splice(0, e);
				var ba = a.completedBoundaries;
				for (e = 0; e < ba.length; e++) if (!Pb(a, b, ba[e])) {
					a.destination = null;
					e++;
					ba.splice(0, e);
					return;
				}
				ba.splice(0, e);
				var ca = a.partialBoundaries;
				for (e = 0; e < ca.length; e++) {
					var mb = ca[e];
					a: {
						f = a;
						g = b;
						var da = mb.completedSegments;
						for (h = 0; h < da.length; h++) if (!Qb(f, g, mb, da[h])) {
							h++;
							da.splice(0, h);
							var nb = !1;
							break a;
						}
						da.splice(0, h);
						nb = !0;
					}
					if (!nb) {
						a.destination = null;
						e++;
						ca.splice(0, e);
						return;
					}
				}
				ca.splice(0, e);
				var ea = a.completedBoundaries;
				for (e = 0; e < ea.length; e++) if (!Pb(a, b, ea[e])) {
					a.destination = null;
					e++;
					ea.splice(0, e);
					return;
				}
				ea.splice(0, e);
			} finally {
				0 === a.allPendingTasks && 0 === a.pingedTasks.length && 0 === a.clientRenderedBoundaries.length && 0 === a.completedBoundaries.length && b.push(null);
			}
		}
		function Rb(a, b) {
			try {
				var c = a.abortableTasks;
				c.forEach(function(c) {
					return Lb(c, a, b);
				});
				c.clear();
				null !== a.destination && Mb(a, a.destination);
			} catch (d) {
				V(a, d), W(a, d);
			}
		}
		function Sb() {}
		function Tb(a, b, c, d) {
			var f = !1, e = null, g = "", h = {
				push: function(a) {
					null !== a && (g += a);
					return !0;
				},
				destroy: function(a) {
					f = !0;
					e = a;
				}
			}, k = !1;
			a = Ab(a, Ea(c, b ? b.identifierPrefix : void 0), {
				insertionMode: 1,
				selectedValue: null
			}, Infinity, Sb, void 0, function() {
				k = !0;
			}, void 0, void 0);
			Cb(a);
			Rb(a, d);
			if (1 === a.status) a.status = 2, h.destroy(a.fatalError);
			else if (2 !== a.status && null === a.destination) {
				a.destination = h;
				try {
					Mb(a, h);
				} catch (m) {
					V(a, m), W(a, m);
				}
			}
			if (f) throw e;
			if (!k) throw Error(l(426));
			return g;
		}
		exports.renderToNodeStream = function() {
			throw Error(l(207));
		};
		exports.renderToStaticMarkup = function(a, b) {
			return Tb(a, b, !0, "The server used \"renderToStaticMarkup\" which does not support Suspense. If you intended to have the server wait for the suspended component please switch to \"renderToReadableStream\" which supports Suspense on the server");
		};
		exports.renderToStaticNodeStream = function() {
			throw Error(l(208));
		};
		exports.renderToString = function(a, b) {
			return Tb(a, b, !1, "The server used \"renderToString\" which does not support Suspense. If you intended for this Suspense boundary to render the fallback content on the server consider throwing an Error somewhere within the Suspense boundary. If you intended to have the server wait for the suspended component please switch to \"renderToReadableStream\" which supports Suspense on the server");
		};
		exports.version = "18.3.1";
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react-dom@18.3.1_react@18.3.1/node_modules/react-dom/cjs/react-dom-server.browser.production.min.js
	/**
	* @license React
	* react-dom-server.browser.production.min.js
	*
	* Copyright (c) Facebook, Inc. and its affiliates.
	*
	* This source code is licensed under the MIT license found in the
	* LICENSE file in the root directory of this source tree.
	*/
	var require_react_dom_server_browser_production_min = /* @__PURE__ */ __commonJSMin(((exports) => {
		var aa = require_react();
		function k(a) {
			for (var b = "https://reactjs.org/docs/error-decoder.html?invariant=" + a, c = 1; c < arguments.length; c++) b += "&args[]=" + encodeURIComponent(arguments[c]);
			return "Minified React error #" + a + "; visit " + b + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
		}
		var l = null;
		var n = 0;
		function p(a, b) {
			if (0 !== b.length) if (512 < b.length) 0 < n && (a.enqueue(new Uint8Array(l.buffer, 0, n)), l = /* @__PURE__ */ new Uint8Array(512), n = 0), a.enqueue(b);
			else {
				var c = l.length - n;
				c < b.length && (0 === c ? a.enqueue(l) : (l.set(b.subarray(0, c), n), a.enqueue(l), b = b.subarray(c)), l = /* @__PURE__ */ new Uint8Array(512), n = 0);
				l.set(b, n);
				n += b.length;
			}
		}
		function t(a, b) {
			p(a, b);
			return !0;
		}
		function ba(a) {
			l && 0 < n && (a.enqueue(new Uint8Array(l.buffer, 0, n)), l = null, n = 0);
		}
		var ca = new TextEncoder();
		function u(a) {
			return ca.encode(a);
		}
		function w(a) {
			return ca.encode(a);
		}
		function da(a, b) {
			"function" === typeof a.error ? a.error(b) : a.close();
		}
		var x = Object.prototype.hasOwnProperty;
		var ea = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/;
		var fa = {};
		var ha = {};
		function ia(a) {
			if (x.call(ha, a)) return !0;
			if (x.call(fa, a)) return !1;
			if (ea.test(a)) return ha[a] = !0;
			fa[a] = !0;
			return !1;
		}
		function y(a, b, c, d, f, e, g) {
			this.acceptsBooleans = 2 === b || 3 === b || 4 === b;
			this.attributeName = d;
			this.attributeNamespace = f;
			this.mustUseProperty = c;
			this.propertyName = a;
			this.type = b;
			this.sanitizeURL = e;
			this.removeEmptyString = g;
		}
		var z = {};
		"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(a) {
			z[a] = new y(a, 0, !1, a, null, !1, !1);
		});
		[
			["acceptCharset", "accept-charset"],
			["className", "class"],
			["htmlFor", "for"],
			["httpEquiv", "http-equiv"]
		].forEach(function(a) {
			var b = a[0];
			z[b] = new y(b, 1, !1, a[1], null, !1, !1);
		});
		[
			"contentEditable",
			"draggable",
			"spellCheck",
			"value"
		].forEach(function(a) {
			z[a] = new y(a, 2, !1, a.toLowerCase(), null, !1, !1);
		});
		[
			"autoReverse",
			"externalResourcesRequired",
			"focusable",
			"preserveAlpha"
		].forEach(function(a) {
			z[a] = new y(a, 2, !1, a, null, !1, !1);
		});
		"allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(a) {
			z[a] = new y(a, 3, !1, a.toLowerCase(), null, !1, !1);
		});
		[
			"checked",
			"multiple",
			"muted",
			"selected"
		].forEach(function(a) {
			z[a] = new y(a, 3, !0, a, null, !1, !1);
		});
		["capture", "download"].forEach(function(a) {
			z[a] = new y(a, 4, !1, a, null, !1, !1);
		});
		[
			"cols",
			"rows",
			"size",
			"span"
		].forEach(function(a) {
			z[a] = new y(a, 6, !1, a, null, !1, !1);
		});
		["rowSpan", "start"].forEach(function(a) {
			z[a] = new y(a, 5, !1, a.toLowerCase(), null, !1, !1);
		});
		var ja = /[\-:]([a-z])/g;
		function ka(a) {
			return a[1].toUpperCase();
		}
		"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(a) {
			var b = a.replace(ja, ka);
			z[b] = new y(b, 1, !1, a, null, !1, !1);
		});
		"xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(a) {
			var b = a.replace(ja, ka);
			z[b] = new y(b, 1, !1, a, "http://www.w3.org/1999/xlink", !1, !1);
		});
		[
			"xml:base",
			"xml:lang",
			"xml:space"
		].forEach(function(a) {
			var b = a.replace(ja, ka);
			z[b] = new y(b, 1, !1, a, "http://www.w3.org/XML/1998/namespace", !1, !1);
		});
		["tabIndex", "crossOrigin"].forEach(function(a) {
			z[a] = new y(a, 1, !1, a.toLowerCase(), null, !1, !1);
		});
		z.xlinkHref = new y("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1);
		[
			"src",
			"href",
			"action",
			"formAction"
		].forEach(function(a) {
			z[a] = new y(a, 1, !1, a.toLowerCase(), null, !0, !0);
		});
		var B = {
			animationIterationCount: !0,
			aspectRatio: !0,
			borderImageOutset: !0,
			borderImageSlice: !0,
			borderImageWidth: !0,
			boxFlex: !0,
			boxFlexGroup: !0,
			boxOrdinalGroup: !0,
			columnCount: !0,
			columns: !0,
			flex: !0,
			flexGrow: !0,
			flexPositive: !0,
			flexShrink: !0,
			flexNegative: !0,
			flexOrder: !0,
			gridArea: !0,
			gridRow: !0,
			gridRowEnd: !0,
			gridRowSpan: !0,
			gridRowStart: !0,
			gridColumn: !0,
			gridColumnEnd: !0,
			gridColumnSpan: !0,
			gridColumnStart: !0,
			fontWeight: !0,
			lineClamp: !0,
			lineHeight: !0,
			opacity: !0,
			order: !0,
			orphans: !0,
			tabSize: !0,
			widows: !0,
			zIndex: !0,
			zoom: !0,
			fillOpacity: !0,
			floodOpacity: !0,
			stopOpacity: !0,
			strokeDasharray: !0,
			strokeDashoffset: !0,
			strokeMiterlimit: !0,
			strokeOpacity: !0,
			strokeWidth: !0
		};
		var la = [
			"Webkit",
			"ms",
			"Moz",
			"O"
		];
		Object.keys(B).forEach(function(a) {
			la.forEach(function(b) {
				b = b + a.charAt(0).toUpperCase() + a.substring(1);
				B[b] = B[a];
			});
		});
		var oa = /["'&<>]/;
		function C(a) {
			if ("boolean" === typeof a || "number" === typeof a) return "" + a;
			a = "" + a;
			var b = oa.exec(a);
			if (b) {
				var c = "", d, f = 0;
				for (d = b.index; d < a.length; d++) {
					switch (a.charCodeAt(d)) {
						case 34:
							b = "&quot;";
							break;
						case 38:
							b = "&amp;";
							break;
						case 39:
							b = "&#x27;";
							break;
						case 60:
							b = "&lt;";
							break;
						case 62:
							b = "&gt;";
							break;
						default: continue;
					}
					f !== d && (c += a.substring(f, d));
					f = d + 1;
					c += b;
				}
				a = f !== d ? c + a.substring(f, d) : c;
			}
			return a;
		}
		var pa = /([A-Z])/g;
		var qa = /^ms-/;
		var ra = Array.isArray;
		var sa = w("<script>");
		var ta = w("<\/script>");
		var ua = w("<script src=\"");
		var va = w("<script type=\"module\" src=\"");
		var wa = w("\" async=\"\"><\/script>");
		var xa = /(<\/|<)(s)(cript)/gi;
		function ya(a, b, c, d) {
			return "" + b + ("s" === c ? "\\u0073" : "\\u0053") + d;
		}
		function za(a, b, c, d, f) {
			a = void 0 === a ? "" : a;
			b = void 0 === b ? sa : w("<script nonce=\"" + C(b) + "\">");
			var e = [];
			void 0 !== c && e.push(b, u(("" + c).replace(xa, ya)), ta);
			if (void 0 !== d) for (c = 0; c < d.length; c++) e.push(ua, u(C(d[c])), wa);
			if (void 0 !== f) for (d = 0; d < f.length; d++) e.push(va, u(C(f[d])), wa);
			return {
				bootstrapChunks: e,
				startInlineScript: b,
				placeholderPrefix: w(a + "P:"),
				segmentPrefix: w(a + "S:"),
				boundaryPrefix: a + "B:",
				idPrefix: a,
				nextSuspenseID: 0,
				sentCompleteSegmentFunction: !1,
				sentCompleteBoundaryFunction: !1,
				sentClientRenderFunction: !1
			};
		}
		function D(a, b) {
			return {
				insertionMode: a,
				selectedValue: b
			};
		}
		function Aa(a) {
			return D("http://www.w3.org/2000/svg" === a ? 2 : "http://www.w3.org/1998/Math/MathML" === a ? 3 : 0, null);
		}
		function Ba(a, b, c) {
			switch (b) {
				case "select": return D(1, null != c.value ? c.value : c.defaultValue);
				case "svg": return D(2, null);
				case "math": return D(3, null);
				case "foreignObject": return D(1, null);
				case "table": return D(4, null);
				case "thead":
				case "tbody":
				case "tfoot": return D(5, null);
				case "colgroup": return D(7, null);
				case "tr": return D(6, null);
			}
			return 4 <= a.insertionMode || 0 === a.insertionMode ? D(1, null) : a;
		}
		var Ca = w("<!-- -->");
		function Da(a, b, c, d) {
			if ("" === b) return d;
			d && a.push(Ca);
			a.push(u(C(b)));
			return !0;
		}
		var Ea = /* @__PURE__ */ new Map();
		var Fa = w(" style=\"");
		var Ga = w(":");
		var Ha = w(";");
		function Ia(a, b, c) {
			if ("object" !== typeof c) throw Error(k(62));
			b = !0;
			for (var d in c) if (x.call(c, d)) {
				var f = c[d];
				if (null != f && "boolean" !== typeof f && "" !== f) {
					if (0 === d.indexOf("--")) {
						var e = u(C(d));
						f = u(C(("" + f).trim()));
					} else {
						e = d;
						var g = Ea.get(e);
						void 0 !== g ? e = g : (g = w(C(e.replace(pa, "-$1").toLowerCase().replace(qa, "-ms-"))), Ea.set(e, g), e = g);
						f = "number" === typeof f ? 0 === f || x.call(B, d) ? u("" + f) : u(f + "px") : u(C(("" + f).trim()));
					}
					b ? (b = !1, a.push(Fa, e, Ga, f)) : a.push(Ha, e, Ga, f);
				}
			}
			b || a.push(E);
		}
		var H = w(" ");
		var I = w("=\"");
		var E = w("\"");
		var Ja = w("=\"\"");
		function J(a, b, c, d) {
			switch (c) {
				case "style":
					Ia(a, b, d);
					return;
				case "defaultValue":
				case "defaultChecked":
				case "innerHTML":
				case "suppressContentEditableWarning":
				case "suppressHydrationWarning": return;
			}
			if (!(2 < c.length) || "o" !== c[0] && "O" !== c[0] || "n" !== c[1] && "N" !== c[1]) {
				if (b = z.hasOwnProperty(c) ? z[c] : null, null !== b) {
					switch (typeof d) {
						case "function":
						case "symbol": return;
						case "boolean": if (!b.acceptsBooleans) return;
					}
					c = u(b.attributeName);
					switch (b.type) {
						case 3:
							d && a.push(H, c, Ja);
							break;
						case 4:
							!0 === d ? a.push(H, c, Ja) : !1 !== d && a.push(H, c, I, u(C(d)), E);
							break;
						case 5:
							isNaN(d) || a.push(H, c, I, u(C(d)), E);
							break;
						case 6:
							!isNaN(d) && 1 <= d && a.push(H, c, I, u(C(d)), E);
							break;
						default: b.sanitizeURL && (d = "" + d), a.push(H, c, I, u(C(d)), E);
					}
				} else if (ia(c)) {
					switch (typeof d) {
						case "function":
						case "symbol": return;
						case "boolean": if (b = c.toLowerCase().slice(0, 5), "data-" !== b && "aria-" !== b) return;
					}
					a.push(H, u(c), I, u(C(d)), E);
				}
			}
		}
		var K = w(">");
		var Ka = w("/>");
		function L(a, b, c) {
			if (null != b) {
				if (null != c) throw Error(k(60));
				if ("object" !== typeof b || !("__html" in b)) throw Error(k(61));
				b = b.__html;
				null !== b && void 0 !== b && a.push(u("" + b));
			}
		}
		function La(a) {
			var b = "";
			aa.Children.forEach(a, function(a) {
				null != a && (b += a);
			});
			return b;
		}
		var Ma = w(" selected=\"\"");
		function Na(a, b, c, d) {
			a.push(M(c));
			var f = c = null, e;
			for (e in b) if (x.call(b, e)) {
				var g = b[e];
				if (null != g) switch (e) {
					case "children":
						c = g;
						break;
					case "dangerouslySetInnerHTML":
						f = g;
						break;
					default: J(a, d, e, g);
				}
			}
			a.push(K);
			L(a, f, c);
			return "string" === typeof c ? (a.push(u(C(c))), null) : c;
		}
		var Oa = w("\n");
		var Pa = /^[a-zA-Z][a-zA-Z:_\.\-\d]*$/;
		var Qa = /* @__PURE__ */ new Map();
		function M(a) {
			var b = Qa.get(a);
			if (void 0 === b) {
				if (!Pa.test(a)) throw Error(k(65, a));
				b = w("<" + a);
				Qa.set(a, b);
			}
			return b;
		}
		var Ra = w("<!DOCTYPE html>");
		function Sa(a, b, c, d, f) {
			switch (b) {
				case "select":
					a.push(M("select"));
					var e = null, g = null;
					for (r in c) if (x.call(c, r)) {
						var h = c[r];
						if (null != h) switch (r) {
							case "children":
								e = h;
								break;
							case "dangerouslySetInnerHTML":
								g = h;
								break;
							case "defaultValue":
							case "value": break;
							default: J(a, d, r, h);
						}
					}
					a.push(K);
					L(a, g, e);
					return e;
				case "option":
					g = f.selectedValue;
					a.push(M("option"));
					var m = h = null, q = null;
					var r = null;
					for (e in c) if (x.call(c, e)) {
						var v = c[e];
						if (null != v) switch (e) {
							case "children":
								h = v;
								break;
							case "selected":
								q = v;
								break;
							case "dangerouslySetInnerHTML":
								r = v;
								break;
							case "value": m = v;
							default: J(a, d, e, v);
						}
					}
					if (null != g) if (c = null !== m ? "" + m : La(h), ra(g)) {
						for (d = 0; d < g.length; d++) if ("" + g[d] === c) {
							a.push(Ma);
							break;
						}
					} else "" + g === c && a.push(Ma);
					else q && a.push(Ma);
					a.push(K);
					L(a, r, h);
					return h;
				case "textarea":
					a.push(M("textarea"));
					r = g = e = null;
					for (h in c) if (x.call(c, h) && (m = c[h], null != m)) switch (h) {
						case "children":
							r = m;
							break;
						case "value":
							e = m;
							break;
						case "defaultValue":
							g = m;
							break;
						case "dangerouslySetInnerHTML": throw Error(k(91));
						default: J(a, d, h, m);
					}
					null === e && null !== g && (e = g);
					a.push(K);
					if (null != r) {
						if (null != e) throw Error(k(92));
						if (ra(r) && 1 < r.length) throw Error(k(93));
						e = "" + r;
					}
					"string" === typeof e && "\n" === e[0] && a.push(Oa);
					null !== e && a.push(u(C("" + e)));
					return null;
				case "input":
					a.push(M("input"));
					m = r = h = e = null;
					for (g in c) if (x.call(c, g) && (q = c[g], null != q)) switch (g) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(k(399, "input"));
						case "defaultChecked":
							m = q;
							break;
						case "defaultValue":
							h = q;
							break;
						case "checked":
							r = q;
							break;
						case "value":
							e = q;
							break;
						default: J(a, d, g, q);
					}
					null !== r ? J(a, d, "checked", r) : null !== m && J(a, d, "checked", m);
					null !== e ? J(a, d, "value", e) : null !== h && J(a, d, "value", h);
					a.push(Ka);
					return null;
				case "menuitem":
					a.push(M("menuitem"));
					for (var A in c) if (x.call(c, A) && (e = c[A], null != e)) switch (A) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(k(400));
						default: J(a, d, A, e);
					}
					a.push(K);
					return null;
				case "title":
					a.push(M("title"));
					e = null;
					for (v in c) if (x.call(c, v) && (g = c[v], null != g)) switch (v) {
						case "children":
							e = g;
							break;
						case "dangerouslySetInnerHTML": throw Error(k(434));
						default: J(a, d, v, g);
					}
					a.push(K);
					return e;
				case "listing":
				case "pre":
					a.push(M(b));
					g = e = null;
					for (m in c) if (x.call(c, m) && (h = c[m], null != h)) switch (m) {
						case "children":
							e = h;
							break;
						case "dangerouslySetInnerHTML":
							g = h;
							break;
						default: J(a, d, m, h);
					}
					a.push(K);
					if (null != g) {
						if (null != e) throw Error(k(60));
						if ("object" !== typeof g || !("__html" in g)) throw Error(k(61));
						c = g.__html;
						null !== c && void 0 !== c && ("string" === typeof c && 0 < c.length && "\n" === c[0] ? a.push(Oa, u(c)) : a.push(u("" + c)));
					}
					"string" === typeof e && "\n" === e[0] && a.push(Oa);
					return e;
				case "area":
				case "base":
				case "br":
				case "col":
				case "embed":
				case "hr":
				case "img":
				case "keygen":
				case "link":
				case "meta":
				case "param":
				case "source":
				case "track":
				case "wbr":
					a.push(M(b));
					for (var F in c) if (x.call(c, F) && (e = c[F], null != e)) switch (F) {
						case "children":
						case "dangerouslySetInnerHTML": throw Error(k(399, b));
						default: J(a, d, F, e);
					}
					a.push(Ka);
					return null;
				case "annotation-xml":
				case "color-profile":
				case "font-face":
				case "font-face-src":
				case "font-face-uri":
				case "font-face-format":
				case "font-face-name":
				case "missing-glyph": return Na(a, c, b, d);
				case "html": return 0 === f.insertionMode && a.push(Ra), Na(a, c, b, d);
				default:
					if (-1 === b.indexOf("-") && "string" !== typeof c.is) return Na(a, c, b, d);
					a.push(M(b));
					g = e = null;
					for (q in c) if (x.call(c, q) && (h = c[q], null != h)) switch (q) {
						case "children":
							e = h;
							break;
						case "dangerouslySetInnerHTML":
							g = h;
							break;
						case "style":
							Ia(a, d, h);
							break;
						case "suppressContentEditableWarning":
						case "suppressHydrationWarning": break;
						default: ia(q) && "function" !== typeof h && "symbol" !== typeof h && a.push(H, u(q), I, u(C(h)), E);
					}
					a.push(K);
					L(a, g, e);
					return e;
			}
		}
		var Ta = w("</");
		var Ua = w(">");
		var Va = w("<template id=\"");
		var Wa = w("\"></template>");
		var Xa = w("<!--$-->");
		var Ya = w("<!--$?--><template id=\"");
		var Za = w("\"></template>");
		var $a = w("<!--$!-->");
		var ab = w("<!--/$-->");
		var bb = w("<template");
		var cb = w("\"");
		var db = w(" data-dgst=\"");
		w(" data-msg=\"");
		w(" data-stck=\"");
		var eb = w("></template>");
		function fb(a, b, c) {
			p(a, Ya);
			if (null === c) throw Error(k(395));
			p(a, c);
			return t(a, Za);
		}
		var gb = w("<div hidden id=\"");
		var hb = w("\">");
		var ib = w("</div>");
		var jb = w("<svg aria-hidden=\"true\" style=\"display:none\" id=\"");
		var kb = w("\">");
		var lb = w("</svg>");
		var mb = w("<math aria-hidden=\"true\" style=\"display:none\" id=\"");
		var nb = w("\">");
		var ob = w("</math>");
		var pb = w("<table hidden id=\"");
		var qb = w("\">");
		var rb = w("</table>");
		var sb = w("<table hidden><tbody id=\"");
		var tb = w("\">");
		var ub = w("</tbody></table>");
		var vb = w("<table hidden><tr id=\"");
		var wb = w("\">");
		var xb = w("</tr></table>");
		var yb = w("<table hidden><colgroup id=\"");
		var zb = w("\">");
		var Ab = w("</colgroup></table>");
		function Bb(a, b, c, d) {
			switch (c.insertionMode) {
				case 0:
				case 1: return p(a, gb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, hb);
				case 2: return p(a, jb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, kb);
				case 3: return p(a, mb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, nb);
				case 4: return p(a, pb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, qb);
				case 5: return p(a, sb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, tb);
				case 6: return p(a, vb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, wb);
				case 7: return p(a, yb), p(a, b.segmentPrefix), p(a, u(d.toString(16))), t(a, zb);
				default: throw Error(k(397));
			}
		}
		function Cb(a, b) {
			switch (b.insertionMode) {
				case 0:
				case 1: return t(a, ib);
				case 2: return t(a, lb);
				case 3: return t(a, ob);
				case 4: return t(a, rb);
				case 5: return t(a, ub);
				case 6: return t(a, xb);
				case 7: return t(a, Ab);
				default: throw Error(k(397));
			}
		}
		var Db = w("function $RS(a,b){a=document.getElementById(a);b=document.getElementById(b);for(a.parentNode.removeChild(a);a.firstChild;)b.parentNode.insertBefore(a.firstChild,b);b.parentNode.removeChild(b)};$RS(\"");
		var Eb = w("$RS(\"");
		var Gb = w("\",\"");
		var Hb = w("\")<\/script>");
		var Ib = w("function $RC(a,b){a=document.getElementById(a);b=document.getElementById(b);b.parentNode.removeChild(b);if(a){a=a.previousSibling;var f=a.parentNode,c=a.nextSibling,e=0;do{if(c&&8===c.nodeType){var d=c.data;if(\"/$\"===d)if(0===e)break;else e--;else\"$\"!==d&&\"$?\"!==d&&\"$!\"!==d||e++}d=c.nextSibling;f.removeChild(c);c=d}while(c);for(;b.firstChild;)f.insertBefore(b.firstChild,c);a.data=\"$\";a._reactRetry&&a._reactRetry()}};$RC(\"");
		var Jb = w("$RC(\"");
		var Kb = w("\",\"");
		var Lb = w("\")<\/script>");
		var Mb = w("function $RX(b,c,d,e){var a=document.getElementById(b);a&&(b=a.previousSibling,b.data=\"$!\",a=a.dataset,c&&(a.dgst=c),d&&(a.msg=d),e&&(a.stck=e),b._reactRetry&&b._reactRetry())};$RX(\"");
		var Nb = w("$RX(\"");
		var Ob = w("\"");
		var Pb = w(")<\/script>");
		var Qb = w(",");
		var Rb = /[<\u2028\u2029]/g;
		function Sb(a) {
			return JSON.stringify(a).replace(Rb, function(a) {
				switch (a) {
					case "<": return "\\u003c";
					case "\u2028": return "\\u2028";
					case "\u2029": return "\\u2029";
					default: throw Error("escapeJSStringsForInstructionScripts encountered a match it does not know how to replace. this means the match regex and the replacement characters are no longer in sync. This is a bug in React");
				}
			});
		}
		var N = Object.assign;
		var Tb = Symbol.for("react.element");
		var Ub = Symbol.for("react.portal");
		var Vb = Symbol.for("react.fragment");
		var Wb = Symbol.for("react.strict_mode");
		var Xb = Symbol.for("react.profiler");
		var Yb = Symbol.for("react.provider");
		var Zb = Symbol.for("react.context");
		var $b = Symbol.for("react.forward_ref");
		var ac = Symbol.for("react.suspense");
		var bc = Symbol.for("react.suspense_list");
		var cc = Symbol.for("react.memo");
		var dc = Symbol.for("react.lazy");
		var ec = Symbol.for("react.scope");
		var fc = Symbol.for("react.debug_trace_mode");
		var gc = Symbol.for("react.legacy_hidden");
		var hc = Symbol.for("react.default_value");
		var ic = Symbol.iterator;
		function jc(a) {
			if (null == a) return null;
			if ("function" === typeof a) return a.displayName || a.name || null;
			if ("string" === typeof a) return a;
			switch (a) {
				case Vb: return "Fragment";
				case Ub: return "Portal";
				case Xb: return "Profiler";
				case Wb: return "StrictMode";
				case ac: return "Suspense";
				case bc: return "SuspenseList";
			}
			if ("object" === typeof a) switch (a.$$typeof) {
				case Zb: return (a.displayName || "Context") + ".Consumer";
				case Yb: return (a._context.displayName || "Context") + ".Provider";
				case $b:
					var b = a.render;
					a = a.displayName;
					a || (a = b.displayName || b.name || "", a = "" !== a ? "ForwardRef(" + a + ")" : "ForwardRef");
					return a;
				case cc: return b = a.displayName || null, null !== b ? b : jc(a.type) || "Memo";
				case dc:
					b = a._payload;
					a = a._init;
					try {
						return jc(a(b));
					} catch (c) {}
			}
			return null;
		}
		var kc = {};
		function lc(a, b) {
			a = a.contextTypes;
			if (!a) return kc;
			var c = {}, d;
			for (d in a) c[d] = b[d];
			return c;
		}
		var O = null;
		function P(a, b) {
			if (a !== b) {
				a.context._currentValue = a.parentValue;
				a = a.parent;
				var c = b.parent;
				if (null === a) {
					if (null !== c) throw Error(k(401));
				} else {
					if (null === c) throw Error(k(401));
					P(a, c);
				}
				b.context._currentValue = b.value;
			}
		}
		function mc(a) {
			a.context._currentValue = a.parentValue;
			a = a.parent;
			null !== a && mc(a);
		}
		function nc(a) {
			var b = a.parent;
			null !== b && nc(b);
			a.context._currentValue = a.value;
		}
		function oc(a, b) {
			a.context._currentValue = a.parentValue;
			a = a.parent;
			if (null === a) throw Error(k(402));
			a.depth === b.depth ? P(a, b) : oc(a, b);
		}
		function pc(a, b) {
			var c = b.parent;
			if (null === c) throw Error(k(402));
			a.depth === c.depth ? P(a, c) : pc(a, c);
			b.context._currentValue = b.value;
		}
		function Q(a) {
			var b = O;
			b !== a && (null === b ? nc(a) : null === a ? mc(b) : b.depth === a.depth ? P(b, a) : b.depth > a.depth ? oc(b, a) : pc(b, a), O = a);
		}
		var qc = {
			isMounted: function() {
				return !1;
			},
			enqueueSetState: function(a, b) {
				a = a._reactInternals;
				null !== a.queue && a.queue.push(b);
			},
			enqueueReplaceState: function(a, b) {
				a = a._reactInternals;
				a.replace = !0;
				a.queue = [b];
			},
			enqueueForceUpdate: function() {}
		};
		function rc(a, b, c, d) {
			var f = void 0 !== a.state ? a.state : null;
			a.updater = qc;
			a.props = c;
			a.state = f;
			var e = {
				queue: [],
				replace: !1
			};
			a._reactInternals = e;
			var g = b.contextType;
			a.context = "object" === typeof g && null !== g ? g._currentValue : d;
			g = b.getDerivedStateFromProps;
			"function" === typeof g && (g = g(c, f), f = null === g || void 0 === g ? f : N({}, f, g), a.state = f);
			if ("function" !== typeof b.getDerivedStateFromProps && "function" !== typeof a.getSnapshotBeforeUpdate && ("function" === typeof a.UNSAFE_componentWillMount || "function" === typeof a.componentWillMount)) if (b = a.state, "function" === typeof a.componentWillMount && a.componentWillMount(), "function" === typeof a.UNSAFE_componentWillMount && a.UNSAFE_componentWillMount(), b !== a.state && qc.enqueueReplaceState(a, a.state, null), null !== e.queue && 0 < e.queue.length) if (b = e.queue, g = e.replace, e.queue = null, e.replace = !1, g && 1 === b.length) a.state = b[0];
			else {
				e = g ? b[0] : a.state;
				f = !0;
				for (g = g ? 1 : 0; g < b.length; g++) {
					var h = b[g];
					h = "function" === typeof h ? h.call(a, e, c, d) : h;
					null != h && (f ? (f = !1, e = N({}, e, h)) : N(e, h));
				}
				a.state = e;
			}
			else e.queue = null;
		}
		var sc = {
			id: 1,
			overflow: ""
		};
		function tc(a, b, c) {
			var d = a.id;
			a = a.overflow;
			var f = 32 - uc(d) - 1;
			d &= ~(1 << f);
			c += 1;
			var e = 32 - uc(b) + f;
			if (30 < e) {
				var g = f - f % 5;
				e = (d & (1 << g) - 1).toString(32);
				d >>= g;
				f -= g;
				return {
					id: 1 << 32 - uc(b) + f | c << f | d,
					overflow: e + a
				};
			}
			return {
				id: 1 << e | c << f | d,
				overflow: a
			};
		}
		var uc = Math.clz32 ? Math.clz32 : vc;
		var wc = Math.log;
		var xc = Math.LN2;
		function vc(a) {
			a >>>= 0;
			return 0 === a ? 32 : 31 - (wc(a) / xc | 0) | 0;
		}
		function yc(a, b) {
			return a === b && (0 !== a || 1 / a === 1 / b) || a !== a && b !== b;
		}
		var zc = "function" === typeof Object.is ? Object.is : yc;
		var R = null;
		var Ac = null;
		var Bc = null;
		var S = null;
		var T = !1;
		var Cc = !1;
		var U = 0;
		var V = null;
		var Dc = 0;
		function W() {
			if (null === R) throw Error(k(321));
			return R;
		}
		function Ec() {
			if (0 < Dc) throw Error(k(312));
			return {
				memoizedState: null,
				queue: null,
				next: null
			};
		}
		function Fc() {
			null === S ? null === Bc ? (T = !1, Bc = S = Ec()) : (T = !0, S = Bc) : null === S.next ? (T = !1, S = S.next = Ec()) : (T = !0, S = S.next);
			return S;
		}
		function Gc() {
			Ac = R = null;
			Cc = !1;
			Bc = null;
			Dc = 0;
			S = V = null;
		}
		function Hc(a, b) {
			return "function" === typeof b ? b(a) : b;
		}
		function Ic(a, b, c) {
			R = W();
			S = Fc();
			if (T) {
				var d = S.queue;
				b = d.dispatch;
				if (null !== V && (c = V.get(d), void 0 !== c)) {
					V.delete(d);
					d = S.memoizedState;
					do
						d = a(d, c.action), c = c.next;
					while (null !== c);
					S.memoizedState = d;
					return [d, b];
				}
				return [S.memoizedState, b];
			}
			a = a === Hc ? "function" === typeof b ? b() : b : void 0 !== c ? c(b) : b;
			S.memoizedState = a;
			a = S.queue = {
				last: null,
				dispatch: null
			};
			a = a.dispatch = Jc.bind(null, R, a);
			return [S.memoizedState, a];
		}
		function Kc(a, b) {
			R = W();
			S = Fc();
			b = void 0 === b ? null : b;
			if (null !== S) {
				var c = S.memoizedState;
				if (null !== c && null !== b) {
					var d = c[1];
					a: if (null === d) d = !1;
					else {
						for (var f = 0; f < d.length && f < b.length; f++) if (!zc(b[f], d[f])) {
							d = !1;
							break a;
						}
						d = !0;
					}
					if (d) return c[0];
				}
			}
			a = a();
			S.memoizedState = [a, b];
			return a;
		}
		function Jc(a, b, c) {
			if (25 <= Dc) throw Error(k(301));
			if (a === R) if (Cc = !0, a = {
				action: c,
				next: null
			}, null === V && (V = /* @__PURE__ */ new Map()), c = V.get(b), void 0 === c) V.set(b, a);
			else {
				for (b = c; null !== b.next;) b = b.next;
				b.next = a;
			}
		}
		function Lc() {
			throw Error(k(394));
		}
		function Mc() {}
		var Oc = {
			readContext: function(a) {
				return a._currentValue;
			},
			useContext: function(a) {
				W();
				return a._currentValue;
			},
			useMemo: Kc,
			useReducer: Ic,
			useRef: function(a) {
				R = W();
				S = Fc();
				var b = S.memoizedState;
				return null === b ? (a = { current: a }, S.memoizedState = a) : b;
			},
			useState: function(a) {
				return Ic(Hc, a);
			},
			useInsertionEffect: Mc,
			useLayoutEffect: function() {},
			useCallback: function(a, b) {
				return Kc(function() {
					return a;
				}, b);
			},
			useImperativeHandle: Mc,
			useEffect: Mc,
			useDebugValue: Mc,
			useDeferredValue: function(a) {
				W();
				return a;
			},
			useTransition: function() {
				W();
				return [!1, Lc];
			},
			useId: function() {
				var a = Ac.treeContext;
				var b = a.overflow;
				a = a.id;
				a = (a & ~(1 << 32 - uc(a) - 1)).toString(32) + b;
				var c = Nc;
				if (null === c) throw Error(k(404));
				b = U++;
				a = ":" + c.idPrefix + "R" + a;
				0 < b && (a += "H" + b.toString(32));
				return a + ":";
			},
			useMutableSource: function(a, b) {
				W();
				return b(a._source);
			},
			useSyncExternalStore: function(a, b, c) {
				if (void 0 === c) throw Error(k(407));
				return c();
			}
		};
		var Nc = null;
		var Pc = aa.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentDispatcher;
		function Qc(a) {
			console.error(a);
			return null;
		}
		function X() {}
		function Rc(a, b, c, d, f, e, g, h, m) {
			var q = [], r = /* @__PURE__ */ new Set();
			b = {
				destination: null,
				responseState: b,
				progressiveChunkSize: void 0 === d ? 12800 : d,
				status: 0,
				fatalError: null,
				nextSegmentId: 0,
				allPendingTasks: 0,
				pendingRootTasks: 0,
				completedRootSegment: null,
				abortableTasks: r,
				pingedTasks: q,
				clientRenderedBoundaries: [],
				completedBoundaries: [],
				partialBoundaries: [],
				onError: void 0 === f ? Qc : f,
				onAllReady: void 0 === e ? X : e,
				onShellReady: void 0 === g ? X : g,
				onShellError: void 0 === h ? X : h,
				onFatalError: void 0 === m ? X : m
			};
			c = Sc(b, 0, null, c, !1, !1);
			c.parentFlushed = !0;
			a = Tc(b, a, null, c, r, kc, null, sc);
			q.push(a);
			return b;
		}
		function Tc(a, b, c, d, f, e, g, h) {
			a.allPendingTasks++;
			null === c ? a.pendingRootTasks++ : c.pendingTasks++;
			var m = {
				node: b,
				ping: function() {
					var b = a.pingedTasks;
					b.push(m);
					1 === b.length && Uc(a);
				},
				blockedBoundary: c,
				blockedSegment: d,
				abortSet: f,
				legacyContext: e,
				context: g,
				treeContext: h
			};
			f.add(m);
			return m;
		}
		function Sc(a, b, c, d, f, e) {
			return {
				status: 0,
				id: -1,
				index: b,
				parentFlushed: !1,
				chunks: [],
				children: [],
				formatContext: d,
				boundary: c,
				lastPushedText: f,
				textEmbedded: e
			};
		}
		function Y(a, b) {
			a = a.onError(b);
			if (null != a && "string" !== typeof a) throw Error("onError returned something with a type other than \"string\". onError should return a string and may return null or undefined but must not return anything else. It received something of type \"" + typeof a + "\" instead");
			return a;
		}
		function Vc(a, b) {
			var c = a.onShellError;
			c(b);
			c = a.onFatalError;
			c(b);
			null !== a.destination ? (a.status = 2, da(a.destination, b)) : (a.status = 1, a.fatalError = b);
		}
		function Wc(a, b, c, d, f) {
			R = {};
			Ac = b;
			U = 0;
			for (a = c(d, f); Cc;) Cc = !1, U = 0, Dc += 1, S = null, a = c(d, f);
			Gc();
			return a;
		}
		function Xc(a, b, c, d) {
			var f = c.render(), e = d.childContextTypes;
			if (null !== e && void 0 !== e) {
				var g = b.legacyContext;
				if ("function" !== typeof c.getChildContext) d = g;
				else {
					c = c.getChildContext();
					for (var h in c) if (!(h in e)) throw Error(k(108, jc(d) || "Unknown", h));
					d = N({}, g, c);
				}
				b.legacyContext = d;
				Z(a, b, f);
				b.legacyContext = g;
			} else Z(a, b, f);
		}
		function Yc(a, b) {
			if (a && a.defaultProps) {
				b = N({}, b);
				a = a.defaultProps;
				for (var c in a) void 0 === b[c] && (b[c] = a[c]);
				return b;
			}
			return b;
		}
		function Zc(a, b, c, d, f) {
			if ("function" === typeof c) if (c.prototype && c.prototype.isReactComponent) {
				f = lc(c, b.legacyContext);
				var e = c.contextType;
				e = new c(d, "object" === typeof e && null !== e ? e._currentValue : f);
				rc(e, c, d, f);
				Xc(a, b, e, c);
			} else {
				e = lc(c, b.legacyContext);
				f = Wc(a, b, c, d, e);
				var g = 0 !== U;
				if ("object" === typeof f && null !== f && "function" === typeof f.render && void 0 === f.$$typeof) rc(f, c, d, e), Xc(a, b, f, c);
				else if (g) {
					d = b.treeContext;
					b.treeContext = tc(d, 1, 0);
					try {
						Z(a, b, f);
					} finally {
						b.treeContext = d;
					}
				} else Z(a, b, f);
			}
			else if ("string" === typeof c) {
				f = b.blockedSegment;
				e = Sa(f.chunks, c, d, a.responseState, f.formatContext);
				f.lastPushedText = !1;
				g = f.formatContext;
				f.formatContext = Ba(g, c, d);
				$c(a, b, e);
				f.formatContext = g;
				switch (c) {
					case "area":
					case "base":
					case "br":
					case "col":
					case "embed":
					case "hr":
					case "img":
					case "input":
					case "keygen":
					case "link":
					case "meta":
					case "param":
					case "source":
					case "track":
					case "wbr": break;
					default: f.chunks.push(Ta, u(c), Ua);
				}
				f.lastPushedText = !1;
			} else {
				switch (c) {
					case gc:
					case fc:
					case Wb:
					case Xb:
					case Vb:
						Z(a, b, d.children);
						return;
					case bc:
						Z(a, b, d.children);
						return;
					case ec: throw Error(k(343));
					case ac:
						a: {
							c = b.blockedBoundary;
							f = b.blockedSegment;
							e = d.fallback;
							d = d.children;
							g = /* @__PURE__ */ new Set();
							var h = {
								id: null,
								rootSegmentID: -1,
								parentFlushed: !1,
								pendingTasks: 0,
								forceClientRender: !1,
								completedSegments: [],
								byteSize: 0,
								fallbackAbortableTasks: g,
								errorDigest: null
							}, m = Sc(a, f.chunks.length, h, f.formatContext, !1, !1);
							f.children.push(m);
							f.lastPushedText = !1;
							var q = Sc(a, 0, null, f.formatContext, !1, !1);
							q.parentFlushed = !0;
							b.blockedBoundary = h;
							b.blockedSegment = q;
							try {
								if ($c(a, b, d), q.lastPushedText && q.textEmbedded && q.chunks.push(Ca), q.status = 1, ad(h, q), 0 === h.pendingTasks) break a;
							} catch (r) {
								q.status = 4, h.forceClientRender = !0, h.errorDigest = Y(a, r);
							} finally {
								b.blockedBoundary = c, b.blockedSegment = f;
							}
							b = Tc(a, e, c, m, g, b.legacyContext, b.context, b.treeContext);
							a.pingedTasks.push(b);
						}
						return;
				}
				if ("object" === typeof c && null !== c) switch (c.$$typeof) {
					case $b:
						d = Wc(a, b, c.render, d, f);
						if (0 !== U) {
							c = b.treeContext;
							b.treeContext = tc(c, 1, 0);
							try {
								Z(a, b, d);
							} finally {
								b.treeContext = c;
							}
						} else Z(a, b, d);
						return;
					case cc:
						c = c.type;
						d = Yc(c, d);
						Zc(a, b, c, d, f);
						return;
					case Yb:
						f = d.children;
						c = c._context;
						d = d.value;
						e = c._currentValue;
						c._currentValue = d;
						g = O;
						O = d = {
							parent: g,
							depth: null === g ? 0 : g.depth + 1,
							context: c,
							parentValue: e,
							value: d
						};
						b.context = d;
						Z(a, b, f);
						a = O;
						if (null === a) throw Error(k(403));
						d = a.parentValue;
						a.context._currentValue = d === hc ? a.context._defaultValue : d;
						a = O = a.parent;
						b.context = a;
						return;
					case Zb:
						d = d.children;
						d = d(c._currentValue);
						Z(a, b, d);
						return;
					case dc:
						f = c._init;
						c = f(c._payload);
						d = Yc(c, d);
						Zc(a, b, c, d, void 0);
						return;
				}
				throw Error(k(130, null == c ? c : typeof c, ""));
			}
		}
		function Z(a, b, c) {
			b.node = c;
			if ("object" === typeof c && null !== c) {
				switch (c.$$typeof) {
					case Tb:
						Zc(a, b, c.type, c.props, c.ref);
						return;
					case Ub: throw Error(k(257));
					case dc:
						var d = c._init;
						c = d(c._payload);
						Z(a, b, c);
						return;
				}
				if (ra(c)) {
					bd(a, b, c);
					return;
				}
				null === c || "object" !== typeof c ? d = null : (d = ic && c[ic] || c["@@iterator"], d = "function" === typeof d ? d : null);
				if (d && (d = d.call(c))) {
					c = d.next();
					if (!c.done) {
						var f = [];
						do
							f.push(c.value), c = d.next();
						while (!c.done);
						bd(a, b, f);
					}
					return;
				}
				a = Object.prototype.toString.call(c);
				throw Error(k(31, "[object Object]" === a ? "object with keys {" + Object.keys(c).join(", ") + "}" : a));
			}
			"string" === typeof c ? (d = b.blockedSegment, d.lastPushedText = Da(b.blockedSegment.chunks, c, a.responseState, d.lastPushedText)) : "number" === typeof c && (d = b.blockedSegment, d.lastPushedText = Da(b.blockedSegment.chunks, "" + c, a.responseState, d.lastPushedText));
		}
		function bd(a, b, c) {
			for (var d = c.length, f = 0; f < d; f++) {
				var e = b.treeContext;
				b.treeContext = tc(e, d, f);
				try {
					$c(a, b, c[f]);
				} finally {
					b.treeContext = e;
				}
			}
		}
		function $c(a, b, c) {
			var d = b.blockedSegment.formatContext, f = b.legacyContext, e = b.context;
			try {
				return Z(a, b, c);
			} catch (m) {
				if (Gc(), "object" === typeof m && null !== m && "function" === typeof m.then) {
					c = m;
					var g = b.blockedSegment, h = Sc(a, g.chunks.length, null, g.formatContext, g.lastPushedText, !0);
					g.children.push(h);
					g.lastPushedText = !1;
					a = Tc(a, b.node, b.blockedBoundary, h, b.abortSet, b.legacyContext, b.context, b.treeContext).ping;
					c.then(a, a);
					b.blockedSegment.formatContext = d;
					b.legacyContext = f;
					b.context = e;
					Q(e);
				} else throw b.blockedSegment.formatContext = d, b.legacyContext = f, b.context = e, Q(e), m;
			}
		}
		function cd(a) {
			var b = a.blockedBoundary;
			a = a.blockedSegment;
			a.status = 3;
			dd(this, b, a);
		}
		function ed(a, b, c) {
			var d = a.blockedBoundary;
			a.blockedSegment.status = 3;
			null === d ? (b.allPendingTasks--, 2 !== b.status && (b.status = 2, null !== b.destination && b.destination.close())) : (d.pendingTasks--, d.forceClientRender || (d.forceClientRender = !0, a = void 0 === c ? Error(k(432)) : c, d.errorDigest = b.onError(a), d.parentFlushed && b.clientRenderedBoundaries.push(d)), d.fallbackAbortableTasks.forEach(function(a) {
				return ed(a, b, c);
			}), d.fallbackAbortableTasks.clear(), b.allPendingTasks--, 0 === b.allPendingTasks && (d = b.onAllReady, d()));
		}
		function ad(a, b) {
			if (0 === b.chunks.length && 1 === b.children.length && null === b.children[0].boundary) {
				var c = b.children[0];
				c.id = b.id;
				c.parentFlushed = !0;
				1 === c.status && ad(a, c);
			} else a.completedSegments.push(b);
		}
		function dd(a, b, c) {
			if (null === b) {
				if (c.parentFlushed) {
					if (null !== a.completedRootSegment) throw Error(k(389));
					a.completedRootSegment = c;
				}
				a.pendingRootTasks--;
				0 === a.pendingRootTasks && (a.onShellError = X, b = a.onShellReady, b());
			} else b.pendingTasks--, b.forceClientRender || (0 === b.pendingTasks ? (c.parentFlushed && 1 === c.status && ad(b, c), b.parentFlushed && a.completedBoundaries.push(b), b.fallbackAbortableTasks.forEach(cd, a), b.fallbackAbortableTasks.clear()) : c.parentFlushed && 1 === c.status && (ad(b, c), 1 === b.completedSegments.length && b.parentFlushed && a.partialBoundaries.push(b)));
			a.allPendingTasks--;
			0 === a.allPendingTasks && (a = a.onAllReady, a());
		}
		function Uc(a) {
			if (2 !== a.status) {
				var b = O, c = Pc.current;
				Pc.current = Oc;
				var d = Nc;
				Nc = a.responseState;
				try {
					var f = a.pingedTasks, e = 0;
					for (; e < f.length; e++) {
						var g = f[e];
						var h = a, m = g.blockedSegment;
						if (0 === m.status) {
							Q(g.context);
							try {
								Z(h, g, g.node), m.lastPushedText && m.textEmbedded && m.chunks.push(Ca), g.abortSet.delete(g), m.status = 1, dd(h, g.blockedBoundary, m);
							} catch (G) {
								if (Gc(), "object" === typeof G && null !== G && "function" === typeof G.then) {
									var q = g.ping;
									G.then(q, q);
								} else {
									g.abortSet.delete(g);
									m.status = 4;
									var r = g.blockedBoundary, v = G, A = Y(h, v);
									null === r ? Vc(h, v) : (r.pendingTasks--, r.forceClientRender || (r.forceClientRender = !0, r.errorDigest = A, r.parentFlushed && h.clientRenderedBoundaries.push(r)));
									h.allPendingTasks--;
									if (0 === h.allPendingTasks) {
										var F = h.onAllReady;
										F();
									}
								}
							}
						}
					}
					f.splice(0, e);
					null !== a.destination && fd(a, a.destination);
				} catch (G) {
					Y(a, G), Vc(a, G);
				} finally {
					Nc = d, Pc.current = c, c === Oc && Q(b);
				}
			}
		}
		function gd(a, b, c) {
			c.parentFlushed = !0;
			switch (c.status) {
				case 0:
					var d = c.id = a.nextSegmentId++;
					c.lastPushedText = !1;
					c.textEmbedded = !1;
					a = a.responseState;
					p(b, Va);
					p(b, a.placeholderPrefix);
					a = u(d.toString(16));
					p(b, a);
					return t(b, Wa);
				case 1:
					c.status = 2;
					var f = !0;
					d = c.chunks;
					var e = 0;
					c = c.children;
					for (var g = 0; g < c.length; g++) {
						for (f = c[g]; e < f.index; e++) p(b, d[e]);
						f = hd(a, b, f);
					}
					for (; e < d.length - 1; e++) p(b, d[e]);
					e < d.length && (f = t(b, d[e]));
					return f;
				default: throw Error(k(390));
			}
		}
		function hd(a, b, c) {
			var d = c.boundary;
			if (null === d) return gd(a, b, c);
			d.parentFlushed = !0;
			if (d.forceClientRender) d = d.errorDigest, t(b, $a), p(b, bb), d && (p(b, db), p(b, u(C(d))), p(b, cb)), t(b, eb), gd(a, b, c);
			else if (0 < d.pendingTasks) {
				d.rootSegmentID = a.nextSegmentId++;
				0 < d.completedSegments.length && a.partialBoundaries.push(d);
				var f = a.responseState;
				var e = f.nextSuspenseID++;
				f = w(f.boundaryPrefix + e.toString(16));
				d = d.id = f;
				fb(b, a.responseState, d);
				gd(a, b, c);
			} else if (d.byteSize > a.progressiveChunkSize) d.rootSegmentID = a.nextSegmentId++, a.completedBoundaries.push(d), fb(b, a.responseState, d.id), gd(a, b, c);
			else {
				t(b, Xa);
				c = d.completedSegments;
				if (1 !== c.length) throw Error(k(391));
				hd(a, b, c[0]);
			}
			return t(b, ab);
		}
		function id(a, b, c) {
			Bb(b, a.responseState, c.formatContext, c.id);
			hd(a, b, c);
			return Cb(b, c.formatContext);
		}
		function jd(a, b, c) {
			for (var d = c.completedSegments, f = 0; f < d.length; f++) kd(a, b, c, d[f]);
			d.length = 0;
			a = a.responseState;
			d = c.id;
			c = c.rootSegmentID;
			p(b, a.startInlineScript);
			a.sentCompleteBoundaryFunction ? p(b, Jb) : (a.sentCompleteBoundaryFunction = !0, p(b, Ib));
			if (null === d) throw Error(k(395));
			c = u(c.toString(16));
			p(b, d);
			p(b, Kb);
			p(b, a.segmentPrefix);
			p(b, c);
			return t(b, Lb);
		}
		function kd(a, b, c, d) {
			if (2 === d.status) return !0;
			var f = d.id;
			if (-1 === f) {
				if (-1 === (d.id = c.rootSegmentID)) throw Error(k(392));
				return id(a, b, d);
			}
			id(a, b, d);
			a = a.responseState;
			p(b, a.startInlineScript);
			a.sentCompleteSegmentFunction ? p(b, Eb) : (a.sentCompleteSegmentFunction = !0, p(b, Db));
			p(b, a.segmentPrefix);
			f = u(f.toString(16));
			p(b, f);
			p(b, Gb);
			p(b, a.placeholderPrefix);
			p(b, f);
			return t(b, Hb);
		}
		function fd(a, b) {
			l = /* @__PURE__ */ new Uint8Array(512);
			n = 0;
			try {
				var c = a.completedRootSegment;
				if (null !== c && 0 === a.pendingRootTasks) {
					hd(a, b, c);
					a.completedRootSegment = null;
					var d = a.responseState.bootstrapChunks;
					for (c = 0; c < d.length - 1; c++) p(b, d[c]);
					c < d.length && t(b, d[c]);
				}
				var f = a.clientRenderedBoundaries, e = 0;
				for (; e < f.length; e++) {
					var g = f[e];
					d = b;
					var h = a.responseState, m = g.id, q = g.errorDigest, r = g.errorMessage, v = g.errorComponentStack;
					p(d, h.startInlineScript);
					h.sentClientRenderFunction ? p(d, Nb) : (h.sentClientRenderFunction = !0, p(d, Mb));
					if (null === m) throw Error(k(395));
					p(d, m);
					p(d, Ob);
					if (q || r || v) p(d, Qb), p(d, u(Sb(q || "")));
					if (r || v) p(d, Qb), p(d, u(Sb(r || "")));
					v && (p(d, Qb), p(d, u(Sb(v))));
					if (!t(d, Pb)) {
						a.destination = null;
						e++;
						f.splice(0, e);
						return;
					}
				}
				f.splice(0, e);
				var A = a.completedBoundaries;
				for (e = 0; e < A.length; e++) if (!jd(a, b, A[e])) {
					a.destination = null;
					e++;
					A.splice(0, e);
					return;
				}
				A.splice(0, e);
				ba(b);
				l = /* @__PURE__ */ new Uint8Array(512);
				n = 0;
				var F = a.partialBoundaries;
				for (e = 0; e < F.length; e++) {
					var G = F[e];
					a: {
						f = a;
						g = b;
						var ma = G.completedSegments;
						for (h = 0; h < ma.length; h++) if (!kd(f, g, G, ma[h])) {
							h++;
							ma.splice(0, h);
							var Fb = !1;
							break a;
						}
						ma.splice(0, h);
						Fb = !0;
					}
					if (!Fb) {
						a.destination = null;
						e++;
						F.splice(0, e);
						return;
					}
				}
				F.splice(0, e);
				var na = a.completedBoundaries;
				for (e = 0; e < na.length; e++) if (!jd(a, b, na[e])) {
					a.destination = null;
					e++;
					na.splice(0, e);
					return;
				}
				na.splice(0, e);
			} finally {
				ba(b), 0 === a.allPendingTasks && 0 === a.pingedTasks.length && 0 === a.clientRenderedBoundaries.length && 0 === a.completedBoundaries.length && b.close();
			}
		}
		function ld(a, b) {
			try {
				var c = a.abortableTasks;
				c.forEach(function(c) {
					return ed(c, a, b);
				});
				c.clear();
				null !== a.destination && fd(a, a.destination);
			} catch (d) {
				Y(a, d), Vc(a, d);
			}
		}
		exports.renderToReadableStream = function(a, b) {
			return new Promise(function(c, d) {
				var f, e, g = new Promise(function(a, b) {
					e = a;
					f = b;
				}), h = Rc(a, za(b ? b.identifierPrefix : void 0, b ? b.nonce : void 0, b ? b.bootstrapScriptContent : void 0, b ? b.bootstrapScripts : void 0, b ? b.bootstrapModules : void 0), Aa(b ? b.namespaceURI : void 0), b ? b.progressiveChunkSize : void 0, b ? b.onError : void 0, e, function() {
					var a = new ReadableStream({
						type: "bytes",
						pull: function(a) {
							if (1 === h.status) h.status = 2, da(a, h.fatalError);
							else if (2 !== h.status && null === h.destination) {
								h.destination = a;
								try {
									fd(h, a);
								} catch (A) {
									Y(h, A), Vc(h, A);
								}
							}
						},
						cancel: function() {
							ld(h);
						}
					}, { highWaterMark: 0 });
					a.allReady = g;
					c(a);
				}, function(a) {
					g.catch(function() {});
					d(a);
				}, f);
				if (b && b.signal) {
					var m = b.signal, q = function() {
						ld(h, m.reason);
						m.removeEventListener("abort", q);
					};
					m.addEventListener("abort", q);
				}
				Uc(h);
			});
		};
		exports.version = "18.3.1";
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react-dom@18.3.1_react@18.3.1/node_modules/react-dom/server.browser.js
	var require_server_browser = /* @__PURE__ */ __commonJSMin(((exports) => {
		var l = require_react_dom_server_legacy_browser_production_min();
		var s = require_react_dom_server_browser_production_min();
		exports.version = l.version;
		exports.renderToString = l.renderToString;
		exports.renderToStaticMarkup = l.renderToStaticMarkup;
		exports.renderToNodeStream = l.renderToNodeStream;
		exports.renderToStaticNodeStream = l.renderToStaticNodeStream;
		exports.renderToReadableStream = s.renderToReadableStream;
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react@18.3.1/node_modules/react/cjs/react-jsx-runtime.production.min.js
	/**
	* @license React
	* react-jsx-runtime.production.min.js
	*
	* Copyright (c) Facebook, Inc. and its affiliates.
	*
	* This source code is licensed under the MIT license found in the
	* LICENSE file in the root directory of this source tree.
	*/
	var require_react_jsx_runtime_production_min = /* @__PURE__ */ __commonJSMin(((exports) => {
		var f = require_react();
		var k = Symbol.for("react.element");
		var l = Symbol.for("react.fragment");
		var m = Object.prototype.hasOwnProperty;
		var n = f.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner;
		var p = {
			key: !0,
			ref: !0,
			__self: !0,
			__source: !0
		};
		function q(c, a, g) {
			var b, d = {}, e = null, h = null;
			void 0 !== g && (e = "" + g);
			void 0 !== a.key && (e = "" + a.key);
			void 0 !== a.ref && (h = a.ref);
			for (b in a) m.call(a, b) && !p.hasOwnProperty(b) && (d[b] = a[b]);
			if (c && c.defaultProps) for (b in a = c.defaultProps, a) void 0 === d[b] && (d[b] = a[b]);
			return {
				$$typeof: k,
				type: c,
				key: e,
				ref: h,
				props: d,
				_owner: n.current
			};
		}
		exports.Fragment = l;
		exports.jsx = q;
		exports.jsxs = q;
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/react@18.3.1/node_modules/react/jsx-runtime.js
	var require_jsx_runtime = /* @__PURE__ */ __commonJSMin(((exports, module) => {
		module.exports = require_react_jsx_runtime_production_min();
	}));
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/world/HudBarIcons.tsx
	var import_server_browser = require_server_browser();
	var import_react = require_react();
	var import_jsx_runtime = require_jsx_runtime();
	var INK$2 = "#2b1e16";
	/** RT-3b：所有工具列圖示的淺色圓底（和 6F-7 的潛行月光同色）、細框與半徑（48 格畫布，圓在 8～40 之內）。 */
	var HUD_BACKING = "#d4dbef";
	var HUD_BACKING_EDGE = "#8a94b8";
	var HUD_BACKING_R = 15.5;
	var TAU$4 = Math.PI * 2;
	function seedOf(s) {
		let h = 2166136261;
		for (const ch of s) h = Math.imul(h ^ ch.charCodeAt(0), 16777619);
		return h >>> 0;
	}
	function rng(seed) {
		let s = seed >>> 0;
		return () => (s = Math.imul(s, 1664525) + 1013904223 >>> 0) / 4294967296;
	}
	function wobble(pts, r, amt) {
		return pts.map(([x, y]) => [x + (r() - .5) * amt, y + (r() - .5) * amt]);
	}
	var f$1 = (n) => (Math.round(n * 100) / 100).toString();
	var mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
	/** 樣張 `smooth()` 的 SVG 版：頂點當控制點、邊的中點當端點的二次曲線。 */
	function smoothPath(pts, closed = true) {
		const n = pts.length;
		if (n === 0) return "";
		if (!closed) {
			const first = pts[0];
			let d = `M${f$1(first[0])} ${f$1(first[1])}`;
			for (let i = 1; i < n - 1; i++) {
				const p = pts[i];
				const m = mid(p, pts[i + 1]);
				d += `Q${f$1(p[0])} ${f$1(p[1])} ${f$1(m[0])} ${f$1(m[1])}`;
			}
			const last = pts[n - 1];
			return `${d}L${f$1(last[0])} ${f$1(last[1])}`;
		}
		const m0 = mid(pts[n - 1], pts[0]);
		let d = `M${f$1(m0[0])} ${f$1(m0[1])}`;
		for (let i = 0; i < n; i++) {
			const p = pts[i];
			const m = mid(p, pts[(i + 1) % n]);
			d += `Q${f$1(p[0])} ${f$1(p[1])} ${f$1(m[0])} ${f$1(m[1])}`;
		}
		return `${d}Z`;
	}
	function ellPts(cx, cy, rx, ry, n = 18) {
		return Array.from({ length: n }, (_, i) => [cx + Math.cos(i / n * TAU$4) * rx, cy + Math.sin(i / n * TAU$4) * ry]);
	}
	/** 填色區塊：淡淡的錯位底色＋暗面斜線＋雙描墨線（樣張的 `ink`）。 */
	function Ink({ k, pts, color, opt = {}, clip }) {
		const r = rng(seedOf(k));
		const fill = smoothPath(wobble(pts, r, .7));
		let hatch = null;
		if (opt.shade !== false) {
			const xs = pts.map((p) => p[0]);
			const ys = pts.map((p) => p[1]);
			const x0 = Math.min(...xs);
			const x1 = Math.max(...xs);
			const y0 = Math.min(...ys);
			const y1 = Math.max(...ys);
			const w = x1 - x0;
			const h = y1 - y0;
			if (w > 3 && h > 3) {
				let d = "";
				for (let x = x0 + w * .6; x < x1 + h; x += 1.3) d += `M${f$1(x)} ${f$1(y0)}L${f$1(x - h * .9)} ${f$1(y1)}`;
				const id = `${clip}-${k}`;
				hatch = /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("clipPath", {
					id,
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: smoothPath(pts) })
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d,
					clipPath: `url(#${id})`,
					stroke: "rgba(43,30,22,0.42)",
					strokeWidth: .35,
					fill: "none"
				})] });
			}
		}
		const lw = opt.w ?? .85;
		const line1 = smoothPath(wobble(pts, r, .5));
		const line2 = smoothPath(wobble(pts, r, .85));
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("g", {
			"data-part": k,
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: fill,
					transform: "translate(0.45 0.35)",
					fill: color,
					fillOpacity: .94,
					stroke: "rgba(0,0,0,0.55)",
					strokeOpacity: .35,
					strokeWidth: .9
				}),
				hatch,
				/* @__PURE__ */ (0, import_jsx_runtime.jsxs)("g", {
					fill: "none",
					stroke: INK$2,
					strokeLinejoin: "round",
					strokeLinecap: "round",
					children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
						d: line1,
						strokeWidth: lw
					}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
						d: line2,
						strokeWidth: lw * .45
					})]
				})
			]
		});
	}
	/** 線條（樣張的 `stroke`）；`dash` 為虛線。 */
	function Line({ k, pts, w = .7, color = INK$2, dash }) {
		const d = smoothPath(wobble(pts, rng(seedOf(k)), .35), false);
		return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			"data-part": k,
			d,
			fill: "none",
			stroke: color,
			strokeWidth: w,
			strokeLinecap: "round",
			strokeLinejoin: "round",
			strokeDasharray: dash
		});
	}
	var Dot = ({ x, y, r, color }) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
		cx: x,
		cy: y,
		r,
		fill: color
	});
	var ICONS = {
		I: {
			zh: "背包",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "bag",
					pts: [
						[11, 20],
						[37, 20],
						[40, 40],
						[8, 40]
					],
					color: "#a06a36",
					opt: { w: 1 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "bag-flap",
					pts: [
						[12, 20],
						[36, 20],
						[34, 29],
						[14, 29]
					],
					color: "#8a5a30",
					opt: { w: .8 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "bag-handle",
					pts: [
						[17, 20],
						[18, 11],
						[30, 11],
						[31, 20]
					],
					w: 1.8,
					color: "#5a3a1e"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "bag-clasp",
					pts: [
						[21, 26],
						[27, 26],
						[27, 32],
						[21, 32]
					],
					color: "#e8bb48",
					opt: {
						shade: false,
						w: .6
					}
				})
			] })
		},
		K: {
			zh: "技能",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "book",
					pts: [
						[9, 10],
						[39, 10],
						[39, 40],
						[9, 40]
					],
					color: "#5a3a9a",
					opt: { w: 1 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "book-pages",
					pts: [
						[12, 10],
						[16, 10],
						[16, 40],
						[12, 40]
					],
					color: "#f2e6c8",
					opt: {
						shade: false,
						w: .6
					}
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("g", {
					style: { filter: "drop-shadow(0 0 3px #a898ff)" },
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
						clip: c,
						k: "book-gem",
						pts: [
							[27, 18],
							[33, 25],
							[27, 32],
							[21, 25]
						],
						color: "#c8bcff",
						opt: {
							shade: false,
							w: .7
						}
					})
				})
			] })
		},
		G: {
			zh: "成長",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "grow-stem",
					pts: [[24, 42], [24, 14]],
					w: 2.6,
					color: "#4f8a3a"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "grow-l",
					pts: [
						[24, 30],
						[12, 24],
						[10, 16],
						[20, 20]
					],
					color: "#6aa84a",
					opt: { w: .8 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "grow-r",
					pts: [
						[24, 24],
						[36, 18],
						[38, 10],
						[28, 14]
					],
					color: "#6aa84a",
					opt: { w: .8 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "grow-arrow",
					pts: [
						[24, 4],
						[31, 13],
						[27, 13],
						[27, 18],
						[21, 18],
						[21, 13],
						[17, 13]
					],
					color: "#ffd23a",
					opt: {
						shade: false,
						w: .7
					}
				})
			] })
		},
		J: {
			zh: "任務",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "scroll",
					pts: [
						[12, 12],
						[36, 12],
						[36, 38],
						[12, 38]
					],
					color: "#f2e6c8",
					opt: { w: .9 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "scroll-t",
					pts: [
						[9, 8],
						[39, 8],
						[39, 13],
						[9, 13]
					],
					color: "#8a2f20",
					opt: {
						shade: false,
						w: .7
					}
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "scroll-b",
					pts: [
						[9, 37],
						[39, 37],
						[39, 42],
						[9, 42]
					],
					color: "#8a2f20",
					opt: {
						shade: false,
						w: .7
					}
				}),
				[
					19,
					25,
					31
				].map((y) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: `scroll-l${y}`,
					pts: [[16, y], [30, y]],
					w: .8,
					color: "#8a7a5a"
				}, y)),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "scroll-bang",
					pts: [
						[30, 16],
						[34, 16],
						[33, 26],
						[31, 26]
					],
					color: "#c83a2a",
					opt: {
						shade: false,
						w: .5
					}
				})
			] })
		},
		Y: {
			zh: "影子",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "sh-head",
					pts: ellPts(24, 16, 7, 7, 14),
					color: "#3a3450",
					opt: { w: .9 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "sh-body",
					pts: [
						[12, 42],
						[14, 28],
						[24, 24],
						[34, 28],
						[36, 42]
					],
					color: "#3a3450",
					opt: { w: .9 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "sh-ghost",
					pts: [
						[34, 14],
						[40, 10],
						[44, 16],
						[42, 26]
					],
					w: 1,
					color: "#a898ff",
					dash: "2 2"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dot, {
					x: 21,
					y: 16,
					r: 1.2,
					color: "#c8bcff"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dot, {
					x: 27,
					y: 16,
					r: 1.2,
					color: "#c8bcff"
				})
			] })
		},
		N: {
			zh: "留言",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "note",
					pts: [
						[8, 10],
						[40, 10],
						[40, 32],
						[22, 32],
						[14, 40],
						[15, 32],
						[8, 32]
					],
					color: "#f2e6c8",
					opt: { w: .9 }
				}),
				[17, 23].map((y) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: `note-l${y}`,
					pts: [[13, y], [35, y]],
					w: .8,
					color: "#8a7a5a"
				}, y)),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "note-pin",
					pts: ellPts(36, 12, 3, 3, 10),
					color: "#c83a2a",
					opt: {
						shade: false,
						w: .5
					}
				})
			] })
		},
		R: {
			zh: "潛行",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "sneak-hood",
					pts: [
						[14, 22],
						[18, 10],
						[30, 8],
						[38, 18],
						[36, 30],
						[24, 26]
					],
					color: "#3a3a44",
					opt: { w: .9 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "sneak-face",
					pts: [
						[22, 18],
						[32, 16],
						[33, 24],
						[24, 25]
					],
					color: "#1a1a20",
					opt: {
						shade: false,
						w: .5
					}
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dot, {
					x: 26,
					y: 20,
					r: 1.1,
					color: "#c8f0ff"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dot, {
					x: 30,
					y: 20,
					r: 1.1,
					color: "#c8f0ff"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "sneak-trail",
					pts: [
						[8, 40],
						[18, 36],
						[28, 40],
						[40, 36]
					],
					w: 1.2,
					color: "#8a8aa8",
					dash: "3 3"
				})
			] })
		},
		M: {
			zh: "地圖",
			draw: (c) => /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Ink, {
					clip: c,
					k: "map",
					pts: [
						[6, 12],
						[18, 8],
						[30, 12],
						[42, 8],
						[42, 38],
						[30, 42],
						[18, 38],
						[6, 42]
					],
					color: "#e8dcb8",
					opt: { w: .9 }
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "map-f1",
					pts: [[18, 8], [18, 38]],
					w: .7,
					color: "#8a7a5a"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "map-f2",
					pts: [[30, 12], [30, 42]],
					w: .7,
					color: "#8a7a5a"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Line, {
					k: "map-route",
					pts: [
						[10, 34],
						[16, 26],
						[24, 28],
						[34, 18]
					],
					w: 1,
					color: "#8a6a3a"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("g", {
					style: { filter: "drop-shadow(0 0 2px #5ac8f0)" },
					children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(Dot, {
						x: 34,
						y: 18,
						r: 3,
						color: "#5aa0ff"
					})
				})
			] })
		}
	};
	/** 樣張的順序：I K G J Y N R M。 */
	var HUD_BAR_ORDER = [
		"I",
		"K",
		"G",
		"J",
		"Y",
		"N",
		"R",
		"M"
	];
	function hudBarName(key) {
		return ICONS[key].zh;
	}
	/** 功能列的定稿圖示（48×48 畫布，依 `size` 縮放）。 */
	function HudBarIcon({ k, size = 25 }) {
		const clip = `hudbar${(0, import_react.useId)().replace(/:/g, "")}`;
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
			className: "hud-icon hud-bar-icon",
			viewBox: "0 0 48 48",
			width: size,
			height: size,
			"aria-hidden": "true",
			"data-bar-icon": k,
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				className: `hud-bar-backing${k === "R" ? " sneak-moon" : ""}`,
				cx: 24,
				cy: 24,
				r: HUD_BACKING_R,
				fill: HUD_BACKING,
				stroke: HUD_BACKING_EDGE,
				strokeWidth: 1
			}), ICONS[k].draw(clip)]
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/world/HudIcons.tsx
	var PATHS$1 = {
		bag: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M8 8V6a4 4 0 0 1 8 0v2",
				fill: "none",
				stroke: "#e8d3a0",
				strokeWidth: "1.8"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "4",
				y: "8",
				width: "16",
				height: "13",
				rx: "3",
				fill: "#a8743c",
				stroke: "#3a2410",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "9",
				y: "12",
				width: "6",
				height: "4",
				rx: "1",
				fill: "#e8bb48"
			})
		] }),
		book: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "5",
				y: "3",
				width: "14",
				height: "18",
				rx: "2",
				fill: "#6a48b8",
				stroke: "#2a1a50",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "8",
				y: "3",
				width: "2",
				height: "18",
				fill: "#3a2870"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M13 8l1.2 2.4 2.6.4-1.9 1.8.5 2.6-2.4-1.3-2.3 1.3.4-2.6-1.9-1.8 2.6-.4z",
				fill: "#e8bb48"
			})
		] }),
		growth: /* @__PURE__ */ (0, import_jsx_runtime.jsx)(import_jsx_runtime.Fragment, { children: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 3l7 8h-4v9H9v-9H5z",
			fill: "#4ac05a",
			stroke: "#1a4a20",
			strokeWidth: "1.2"
		}) }),
		scroll: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
			x: "4",
			y: "5",
			width: "16",
			height: "14",
			rx: "2",
			fill: "#e8d3a0",
			stroke: "#5a3a1a",
			strokeWidth: "1.2"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M7 9h10M7 12h10M7 15h6",
			stroke: "#a8442c",
			strokeWidth: "1.6"
		})] }),
		shadow: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "8",
				r: "4",
				fill: "#5a4a90"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M4 21c0-5 3.5-8 8-8s8 3 8 8z",
				fill: "#5a4a90"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "8",
				r: "4",
				fill: "none",
				stroke: "#b8a0ff",
				strokeWidth: "1.2",
				strokeDasharray: "2 1.5"
			})
		] }),
		notes: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M4 5h16v11H11l-5 4v-4H4z",
				fill: "#f0ead8",
				stroke: "#5a4a30",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "8.5",
				cy: "10.5",
				r: "1.2",
				fill: "#5a4a30"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "10.5",
				r: "1.2",
				fill: "#5a4a30"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "15.5",
				cy: "10.5",
				r: "1.2",
				fill: "#5a4a30"
			})
		] }),
		boots: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M8 3h6v11l5 2v4H6V14z",
			fill: "#8a5a2a",
			stroke: "#3a2410",
			strokeWidth: "1.2"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M8 7h6",
			stroke: "#e8bb48",
			strokeWidth: "1.4"
		})] }),
		map: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z",
				fill: "#e8d3a0",
				stroke: "#5a3a1a",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M9 4v14M15 6v14",
				stroke: "#a8875a",
				strokeWidth: "1"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M11 10l3 3m0-3l-3 3",
				stroke: "#c03a2a",
				strokeWidth: "1.6"
			})
		] }),
		gear: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "12",
				r: "6.5",
				fill: "none",
				stroke: "#c8c0b0",
				strokeWidth: "3",
				strokeDasharray: "2.6 2.5"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "12",
				r: "4.5",
				fill: "#8a8478"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
				cx: "12",
				cy: "12",
				r: "1.8",
				fill: "#2a2620"
			})
		] }),
		coin: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "8",
			fill: "#e8bb48",
			stroke: "#7a5a10",
			strokeWidth: "1.4"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
			x: "10",
			y: "8",
			width: "4",
			height: "8",
			rx: "1",
			fill: "none",
			stroke: "#7a5a10",
			strokeWidth: "1.4"
		})] }),
		token: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "8",
			fill: "#a04a3a",
			stroke: "#4a1a10",
			strokeWidth: "1.4"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 6.5l1.6 3.4 3.7.4-2.8 2.5.8 3.6L12 14.6l-3.3 1.8.8-3.6-2.8-2.5 3.7-.4z",
			fill: "#f0c8a0"
		})] }),
		ration: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("ellipse", {
			cx: "12",
			cy: "13",
			rx: "8",
			ry: "5.5",
			fill: "#c08a4a",
			stroke: "#5a3a1a",
			strokeWidth: "1.2"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M8 11.5c1 1 2 1 3 0m2 0c1 1 2 1 3 0",
			stroke: "#5a3a1a",
			strokeWidth: "1.2",
			fill: "none"
		})] }),
		bulb: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 3a6 6 0 0 0-3.5 10.9V16h7v-2.1A6 6 0 0 0 12 3z",
			fill: "#ffe070",
			stroke: "#7a5a10",
			strokeWidth: "1.2"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
			x: "9",
			y: "17",
			width: "6",
			height: "3",
			rx: "1",
			fill: "#8a8478"
		})] }),
		warn: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M12 3l10 18H2z",
				fill: "#e8bb48",
				stroke: "#5a3a00",
				strokeWidth: "1.2",
				strokeLinejoin: "round"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "11",
				y: "9",
				width: "2",
				height: "6",
				fill: "#3a2400"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "11",
				y: "16.5",
				width: "2",
				height: "2",
				fill: "#3a2400"
			})
		] }),
		sun: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "5",
			fill: "#ffd040"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M5 19l2-2M17 7l2-2",
			stroke: "#ffd040",
			strokeWidth: "1.8"
		})] }),
		moon: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M15 3a9 9 0 1 0 6 13A7 7 0 0 1 15 3z",
			fill: "#d8dcf0",
			stroke: "#5a6090",
			strokeWidth: "1"
		}),
		clear: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "4",
			fill: "#ffd040"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "7",
			fill: "none",
			stroke: "#ffd040",
			strokeWidth: "1.2",
			strokeDasharray: "1.5 2"
		})] }),
		rain: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M6 13a4 4 0 0 1 .5-8 5 5 0 0 1 9.5 1A3.5 3.5 0 0 1 17 13z",
			fill: "#b8c4d0"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M8 16l-1 3M12 16l-1 3M16 16l-1 3",
			stroke: "#5a9ae0",
			strokeWidth: "1.8"
		})] }),
		fog: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M3 8h14M6 12h15M3 16h13M7 20h10",
			stroke: "#c8ccd0",
			strokeWidth: "2",
			strokeLinecap: "round"
		}),
		snow: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 3v18M4 7.5l16 9M4 16.5l16-9",
			stroke: "#e0f0ff",
			strokeWidth: "1.8"
		}),
		wind: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M3 9h12a3 3 0 1 0-3-3M3 14h16a3 3 0 1 1-3 3",
			stroke: "#c8ccd0",
			strokeWidth: "1.8",
			fill: "none"
		}),
		night: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M15 3a9 9 0 1 0 6 13A7 7 0 0 1 15 3z",
			fill: "#8a90c0"
		}),
		rank: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M5 4h14v8c0 4-3.5 7-7 8-3.5-1-7-4-7-8z",
			fill: "#4a6ad0",
			stroke: "#e8bb48",
			strokeWidth: "1.4"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M9 10l3-3 3 3M9 14l3-3 3 3",
			stroke: "#e8bb48",
			strokeWidth: "1.4",
			fill: "none"
		})] }),
		pin: /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M14 2l8 8-3 1-4 4 .5 4-1.5 1.5-4-4-5 5-1-1 5-5-4-4L7 9.5l4 .5 4-4z",
			fill: "#c8a868"
		}),
		town: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M3 11l9-7 9 7",
				fill: "none",
				stroke: "#e8d3a0",
				strokeWidth: "1.8"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "6",
				y: "11",
				width: "12",
				height: "9",
				fill: "#7fa8d0",
				stroke: "#2a3a50",
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
				x: "10.5",
				y: "14",
				width: "3",
				height: "6",
				fill: "#2a3a50"
			})
		] })
	};
	function HudIcon({ name, size = 22 }) {
		return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
			className: "hud-icon",
			viewBox: "0 0 24 24",
			width: size,
			height: size,
			"aria-hidden": "true",
			"data-icon": name,
			children: PATHS$1[name]
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/ui/BattleToolIcons.tsx
	var GOLD$8 = "#e8cf90";
	var PATHS = {
		reactions: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 2.5l8 3v6c0 5-3.6 8.6-8 10-4.4-1.4-8-5-8-10v-6z",
			fill: "#3a3020",
			stroke: GOLD$8,
			strokeWidth: "1.5"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M13 6l-4 7h3l-1 5 4-7h-3z",
			fill: "#ffd23f"
		})] }),
		orders: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M6 21V3",
			stroke: GOLD$8,
			strokeWidth: "1.8",
			strokeLinecap: "round"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M6.5 4h11l-2.5 4 2.5 4h-11z",
			fill: "#d85a48",
			stroke: "#6a2018",
			strokeWidth: "1"
		})] }),
		legend: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M12 6c-2.5-1.6-5.5-2-8-1.5v14c2.5-.5 5.5-.1 8 1.5 2.5-1.6 5.5-2 8-1.5v-14c-2.5-.5-5.5-.1-8 1.5z",
				fill: "#3a3020",
				stroke: GOLD$8,
				strokeWidth: "1.4"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M12 6v14",
				stroke: GOLD$8,
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M6.5 9h3M6.5 12h3M14.5 9h3M14.5 12h3",
				stroke: "#c8b888",
				strokeWidth: "1",
				strokeLinecap: "round"
			})
		] }),
		layout: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M12 2.8l1.6 2.4 2.8-.8.6 2.8 2.8.6-.8 2.8 2.4 1.6-2.4 1.6.8 2.8-2.8.6-.6 2.8-2.8-.8L12 21.2l-1.6-2.4-2.8.8-.6-2.8-2.8-.6.8-2.8L2.6 12 5 10.4l-.8-2.8 2.8-.6.6-2.8 2.8.8z",
			fill: "#3a3020",
			stroke: GOLD$8,
			strokeWidth: "1.3",
			strokeLinejoin: "round"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
			cx: "12",
			cy: "12",
			r: "3.2",
			fill: "none",
			stroke: GOLD$8,
			strokeWidth: "1.4"
		})] }),
		save: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M4 4h13l3 3v13H4z",
				fill: "#2a4060",
				stroke: "#a8c8f0",
				strokeWidth: "1.4",
				strokeLinejoin: "round"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M7 4h9v5H7z",
				fill: "#a8c8f0"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M7 13h10v7H7z",
				fill: "#e8eef8"
			})
		] }),
		exit: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M13 3H5v18h8",
			fill: "none",
			stroke: GOLD$8,
			strokeWidth: "1.8",
			strokeLinejoin: "round"
		}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
			d: "M10 12h10M16.5 8l3.5 4-3.5 4",
			fill: "none",
			stroke: "#f0e6d0",
			strokeWidth: "1.9",
			strokeLinecap: "round",
			strokeLinejoin: "round"
		})] }),
		telegraph: /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M6 3h12M6 21h12",
				stroke: GOLD$8,
				strokeWidth: "1.8",
				strokeLinecap: "round"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M7 3.5c0 5 10 5 10 8.5S7 15.5 7 20.5h10c0-5-10-5-10-8.5S17 8.5 17 3.5z",
				fill: "#3a3020",
				stroke: GOLD$8,
				strokeWidth: "1.2"
			}),
			/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M9.5 19.5h5l-2.5-3z",
				fill: "#e8bb48"
			})
		] })
	};
	function BattleToolIcon({ name, size = 20 }) {
		return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("svg", {
			className: "bhud-icon",
			viewBox: "0 0 24 24",
			width: size,
			height: size,
			"aria-hidden": "true",
			"data-icon": name,
			children: PATHS[name]
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/ui/SettingsHead.tsx
	var GOLD$7 = "#e8bb48";
	var INK$1 = "#1c1712";
	function Icon({ name }) {
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
			className: "settings-head-icon",
			viewBox: "0 0 20 20",
			width: 16,
			height: 16,
			"aria-hidden": "true",
			"data-icon": name,
			children: [
				name === "sound" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M3 8h3l4-4v12l-4-4H3z",
					fill: GOLD$7,
					stroke: INK$1,
					strokeWidth: "1",
					strokeLinejoin: "round"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M13 7.5q2 2.5 0 5M15 5.5q4 4.5 0 9",
					fill: "none",
					stroke: GOLD$7,
					strokeWidth: "1.5",
					strokeLinecap: "round"
				})] }),
				name === "motion" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
					cx: "12",
					cy: "10",
					r: "4.5",
					fill: GOLD$7,
					stroke: INK$1,
					strokeWidth: "1"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M2 7h4M1 10h4M2 13h4",
					stroke: GOLD$7,
					strokeWidth: "1.5",
					strokeLinecap: "round",
					opacity: "0.7"
				})] }),
				name === "hint" && /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M10 2a5.5 5.5 0 0 0-3 10.1V14h6v-1.9A5.5 5.5 0 0 0 10 2z",
					fill: GOLD$7,
					stroke: INK$1,
					strokeWidth: "1"
				}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
					x: "7.5",
					y: "15",
					width: "5",
					height: "2.5",
					rx: "1",
					fill: GOLD$7,
					stroke: INK$1,
					strokeWidth: "1"
				})] })
			]
		});
	}
	function SettingsHead({ icon, children }) {
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("div", {
			className: "section-title settings-head",
			"data-settings-head": icon,
			children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)(Icon, { name: icon }), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("span", { children })]
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/identity.js
	var ALIAS = Symbol.for("yaml.alias");
	var DOC = Symbol.for("yaml.document");
	var MAP = Symbol.for("yaml.map");
	var PAIR = Symbol.for("yaml.pair");
	var SCALAR$1 = Symbol.for("yaml.scalar");
	var SEQ = Symbol.for("yaml.seq");
	var NODE_TYPE = Symbol.for("yaml.node.type");
	var isAlias = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === ALIAS;
	var isDocument = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === DOC;
	var isMap = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === MAP;
	var isPair = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === PAIR;
	var isScalar = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SCALAR$1;
	var isSeq = (node) => !!node && typeof node === "object" && node[NODE_TYPE] === SEQ;
	function isCollection(node) {
		if (node && typeof node === "object") switch (node[NODE_TYPE]) {
			case MAP:
			case SEQ: return true;
		}
		return false;
	}
	function isNode(node) {
		if (node && typeof node === "object") switch (node[NODE_TYPE]) {
			case ALIAS:
			case MAP:
			case SCALAR$1:
			case SEQ: return true;
		}
		return false;
	}
	var hasAnchor = (node) => (isScalar(node) || isCollection(node)) && !!node.anchor;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/visit.js
	var BREAK$1 = Symbol("break visit");
	var SKIP$1 = Symbol("skip children");
	var REMOVE$1 = Symbol("remove node");
	/**
	* Apply a visitor to an AST node or document.
	*
	* Walks through the tree (depth-first) starting from `node`, calling a
	* `visitor` function with three arguments:
	*   - `key`: For sequence values and map `Pair`, the node's index in the
	*     collection. Within a `Pair`, `'key'` or `'value'`, correspondingly.
	*     `null` for the root node.
	*   - `node`: The current node.
	*   - `path`: The ancestry of the current node.
	*
	* The return value of the visitor may be used to control the traversal:
	*   - `undefined` (default): Do nothing and continue
	*   - `visit.SKIP`: Do not visit the children of this node, continue with next
	*     sibling
	*   - `visit.BREAK`: Terminate traversal completely
	*   - `visit.REMOVE`: Remove the current node, then continue with the next one
	*   - `Node`: Replace the current node, then continue by visiting it
	*   - `number`: While iterating the items of a sequence or map, set the index
	*     of the next step. This is useful especially if the index of the current
	*     node has changed.
	*
	* If `visitor` is a single function, it will be called with all values
	* encountered in the tree, including e.g. `null` values. Alternatively,
	* separate visitor functions may be defined for each `Map`, `Pair`, `Seq`,
	* `Alias` and `Scalar` node. To define the same visitor function for more than
	* one node type, use the `Collection` (map and seq), `Value` (map, seq & scalar)
	* and `Node` (alias, map, seq & scalar) targets. Of all these, only the most
	* specific defined one will be used for each node.
	*/
	function visit$1(node, visitor) {
		const visitor_ = initVisitor(visitor);
		if (isDocument(node)) {
			if (visit_(null, node.contents, visitor_, Object.freeze([node])) === REMOVE$1) node.contents = null;
		} else visit_(null, node, visitor_, Object.freeze([]));
	}
	/** Terminate visit traversal completely */
	visit$1.BREAK = BREAK$1;
	/** Do not visit the children of the current node */
	visit$1.SKIP = SKIP$1;
	/** Remove the current node */
	visit$1.REMOVE = REMOVE$1;
	function visit_(key, node, visitor, path) {
		const ctrl = callVisitor(key, node, visitor, path);
		if (isNode(ctrl) || isPair(ctrl)) {
			replaceNode(key, path, ctrl);
			return visit_(key, ctrl, visitor, path);
		}
		if (typeof ctrl !== "symbol") {
			if (isCollection(node)) {
				path = Object.freeze(path.concat(node));
				for (let i = 0; i < node.items.length; ++i) {
					const ci = visit_(i, node.items[i], visitor, path);
					if (typeof ci === "number") i = ci - 1;
					else if (ci === BREAK$1) return BREAK$1;
					else if (ci === REMOVE$1) {
						node.items.splice(i, 1);
						i -= 1;
					}
				}
			} else if (isPair(node)) {
				path = Object.freeze(path.concat(node));
				const ck = visit_("key", node.key, visitor, path);
				if (ck === BREAK$1) return BREAK$1;
				else if (ck === REMOVE$1) node.key = null;
				const cv = visit_("value", node.value, visitor, path);
				if (cv === BREAK$1) return BREAK$1;
				else if (cv === REMOVE$1) node.value = null;
			}
		}
		return ctrl;
	}
	/**
	* Apply an async visitor to an AST node or document.
	*
	* Walks through the tree (depth-first) starting from `node`, calling a
	* `visitor` function with three arguments:
	*   - `key`: For sequence values and map `Pair`, the node's index in the
	*     collection. Within a `Pair`, `'key'` or `'value'`, correspondingly.
	*     `null` for the root node.
	*   - `node`: The current node.
	*   - `path`: The ancestry of the current node.
	*
	* The return value of the visitor may be used to control the traversal:
	*   - `Promise`: Must resolve to one of the following values
	*   - `undefined` (default): Do nothing and continue
	*   - `visit.SKIP`: Do not visit the children of this node, continue with next
	*     sibling
	*   - `visit.BREAK`: Terminate traversal completely
	*   - `visit.REMOVE`: Remove the current node, then continue with the next one
	*   - `Node`: Replace the current node, then continue by visiting it
	*   - `number`: While iterating the items of a sequence or map, set the index
	*     of the next step. This is useful especially if the index of the current
	*     node has changed.
	*
	* If `visitor` is a single function, it will be called with all values
	* encountered in the tree, including e.g. `null` values. Alternatively,
	* separate visitor functions may be defined for each `Map`, `Pair`, `Seq`,
	* `Alias` and `Scalar` node. To define the same visitor function for more than
	* one node type, use the `Collection` (map and seq), `Value` (map, seq & scalar)
	* and `Node` (alias, map, seq & scalar) targets. Of all these, only the most
	* specific defined one will be used for each node.
	*/
	async function visitAsync(node, visitor) {
		const visitor_ = initVisitor(visitor);
		if (isDocument(node)) {
			if (await visitAsync_(null, node.contents, visitor_, Object.freeze([node])) === REMOVE$1) node.contents = null;
		} else await visitAsync_(null, node, visitor_, Object.freeze([]));
	}
	/** Terminate visit traversal completely */
	visitAsync.BREAK = BREAK$1;
	/** Do not visit the children of the current node */
	visitAsync.SKIP = SKIP$1;
	/** Remove the current node */
	visitAsync.REMOVE = REMOVE$1;
	async function visitAsync_(key, node, visitor, path) {
		const ctrl = await callVisitor(key, node, visitor, path);
		if (isNode(ctrl) || isPair(ctrl)) {
			replaceNode(key, path, ctrl);
			return visitAsync_(key, ctrl, visitor, path);
		}
		if (typeof ctrl !== "symbol") {
			if (isCollection(node)) {
				path = Object.freeze(path.concat(node));
				for (let i = 0; i < node.items.length; ++i) {
					const ci = await visitAsync_(i, node.items[i], visitor, path);
					if (typeof ci === "number") i = ci - 1;
					else if (ci === BREAK$1) return BREAK$1;
					else if (ci === REMOVE$1) {
						node.items.splice(i, 1);
						i -= 1;
					}
				}
			} else if (isPair(node)) {
				path = Object.freeze(path.concat(node));
				const ck = await visitAsync_("key", node.key, visitor, path);
				if (ck === BREAK$1) return BREAK$1;
				else if (ck === REMOVE$1) node.key = null;
				const cv = await visitAsync_("value", node.value, visitor, path);
				if (cv === BREAK$1) return BREAK$1;
				else if (cv === REMOVE$1) node.value = null;
			}
		}
		return ctrl;
	}
	function initVisitor(visitor) {
		if (typeof visitor === "object" && (visitor.Collection || visitor.Node || visitor.Value)) return Object.assign({
			Alias: visitor.Node,
			Map: visitor.Node,
			Scalar: visitor.Node,
			Seq: visitor.Node
		}, visitor.Value && {
			Map: visitor.Value,
			Scalar: visitor.Value,
			Seq: visitor.Value
		}, visitor.Collection && {
			Map: visitor.Collection,
			Seq: visitor.Collection
		}, visitor);
		return visitor;
	}
	function callVisitor(key, node, visitor, path) {
		if (typeof visitor === "function") return visitor(key, node, path);
		if (isMap(node)) return visitor.Map?.(key, node, path);
		if (isSeq(node)) return visitor.Seq?.(key, node, path);
		if (isPair(node)) return visitor.Pair?.(key, node, path);
		if (isScalar(node)) return visitor.Scalar?.(key, node, path);
		if (isAlias(node)) return visitor.Alias?.(key, node, path);
	}
	function replaceNode(key, path, node) {
		const parent = path[path.length - 1];
		if (isCollection(parent)) parent.items[key] = node;
		else if (isPair(parent)) {
			if (key === "key") parent.key = node;
			else parent.value = node;
		} else if (isDocument(parent)) parent.contents = node;
		else {
			const pt = isAlias(parent) ? "alias" : "scalar";
			throw new Error(`Cannot replace node with ${pt} parent`);
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/doc/directives.js
	var escapeChars = {
		"!": "%21",
		",": "%2C",
		"[": "%5B",
		"]": "%5D",
		"{": "%7B",
		"}": "%7D"
	};
	var escapeTagName = (tn) => tn.replace(/[!,[\]{}]/g, (ch) => escapeChars[ch]);
	var Directives = class Directives {
		constructor(yaml, tags) {
			/**
			* The directives-end/doc-start marker `---`. If `null`, a marker may still be
			* included in the document's stringified representation.
			*/
			this.docStart = null;
			/** The doc-end marker `...`.  */
			this.docEnd = false;
			this.yaml = Object.assign({}, Directives.defaultYaml, yaml);
			this.tags = Object.assign({}, Directives.defaultTags, tags);
		}
		clone() {
			const copy = new Directives(this.yaml, this.tags);
			copy.docStart = this.docStart;
			return copy;
		}
		/**
		* During parsing, get a Directives instance for the current document and
		* update the stream state according to the current version's spec.
		*/
		atDocument() {
			const res = new Directives(this.yaml, this.tags);
			switch (this.yaml.version) {
				case "1.1":
					this.atNextDocument = true;
					break;
				case "1.2":
					this.atNextDocument = false;
					this.yaml = {
						explicit: Directives.defaultYaml.explicit,
						version: "1.2"
					};
					this.tags = Object.assign({}, Directives.defaultTags);
			}
			return res;
		}
		/**
		* @param onError - May be called even if the action was successful
		* @returns `true` on success
		*/
		add(line, onError) {
			if (this.atNextDocument) {
				this.yaml = {
					explicit: Directives.defaultYaml.explicit,
					version: "1.1"
				};
				this.tags = Object.assign({}, Directives.defaultTags);
				this.atNextDocument = false;
			}
			const parts = line.trim().split(/[ \t]+/);
			const name = parts.shift();
			switch (name) {
				case "%TAG": {
					if (parts.length !== 2) {
						onError(0, "%TAG directive should contain exactly two parts");
						if (parts.length < 2) return false;
					}
					const [handle, prefix] = parts;
					this.tags[handle] = prefix;
					return true;
				}
				case "%YAML": {
					this.yaml.explicit = true;
					if (parts.length !== 1) {
						onError(0, "%YAML directive should contain exactly one part");
						return false;
					}
					const [version] = parts;
					if (version === "1.1" || version === "1.2") {
						this.yaml.version = version;
						return true;
					} else {
						const isValid = /^\d+\.\d+$/.test(version);
						onError(6, `Unsupported YAML version ${version}`, isValid);
						return false;
					}
				}
				default:
					onError(0, `Unknown directive ${name}`, true);
					return false;
			}
		}
		/**
		* Resolves a tag, matching handles to those defined in %TAG directives.
		*
		* @returns Resolved tag, which may also be the non-specific tag `'!'` or a
		*   `'!local'` tag, or `null` if unresolvable.
		*/
		tagName(source, onError) {
			if (source === "!") return "!";
			if (source[0] !== "!") {
				onError(`Not a valid tag: ${source}`);
				return null;
			}
			if (source[1] === "<") {
				const verbatim = source.slice(2, -1);
				if (verbatim === "!" || verbatim === "!!") {
					onError(`Verbatim tags aren't resolved, so ${source} is invalid.`);
					return null;
				}
				if (source[source.length - 1] !== ">") onError("Verbatim tags must end with a >");
				return verbatim;
			}
			const [, handle, suffix] = source.match(/^(.*!)([^!]*)$/s);
			if (!suffix) onError(`The ${source} tag has no suffix`);
			const prefix = this.tags[handle];
			if (prefix) try {
				return prefix + decodeURIComponent(suffix);
			} catch (error) {
				onError(String(error));
				return null;
			}
			if (handle === "!") return source;
			onError(`Could not resolve tag: ${source}`);
			return null;
		}
		/**
		* Given a fully resolved tag, returns its printable string form,
		* taking into account current tag prefixes and defaults.
		*/
		tagString(tag) {
			for (const [handle, prefix] of Object.entries(this.tags)) if (tag.startsWith(prefix)) return handle + escapeTagName(tag.substring(prefix.length));
			return tag[0] === "!" ? tag : `!<${tag}>`;
		}
		toString(doc) {
			const lines = this.yaml.explicit ? [`%YAML ${this.yaml.version || "1.2"}`] : [];
			const tagEntries = Object.entries(this.tags);
			let tagNames;
			if (doc && tagEntries.length > 0 && isNode(doc.contents)) {
				const tags = {};
				visit$1(doc.contents, (_key, node) => {
					if (isNode(node) && node.tag) tags[node.tag] = true;
				});
				tagNames = Object.keys(tags);
			} else tagNames = [];
			for (const [handle, prefix] of tagEntries) {
				if (handle === "!!" && prefix === "tag:yaml.org,2002:") continue;
				if (!doc || tagNames.some((tn) => tn.startsWith(prefix))) lines.push(`%TAG ${handle} ${prefix}`);
			}
			return lines.join("\n");
		}
	};
	Directives.defaultYaml = {
		explicit: false,
		version: "1.2"
	};
	Directives.defaultTags = { "!!": "tag:yaml.org,2002:" };
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/doc/anchors.js
	/**
	* Verify that the input string is a valid anchor.
	*
	* Will throw on errors.
	*/
	function anchorIsValid(anchor) {
		if (/[\x00-\x19\s,[\]{}]/.test(anchor)) {
			const msg = `Anchor must not contain whitespace or control characters: ${JSON.stringify(anchor)}`;
			throw new Error(msg);
		}
		return true;
	}
	function anchorNames(root) {
		const anchors = /* @__PURE__ */ new Set();
		visit$1(root, { Value(_key, node) {
			if (node.anchor) anchors.add(node.anchor);
		} });
		return anchors;
	}
	/** Find a new anchor name with the given `prefix` and a one-indexed suffix. */
	function findNewAnchor(prefix, exclude) {
		for (let i = 1;; ++i) {
			const name = `${prefix}${i}`;
			if (!exclude.has(name)) return name;
		}
	}
	function createNodeAnchors(doc, prefix) {
		const aliasObjects = [];
		const sourceObjects = /* @__PURE__ */ new Map();
		let prevAnchors = null;
		return {
			onAnchor: (source) => {
				aliasObjects.push(source);
				prevAnchors ?? (prevAnchors = anchorNames(doc));
				const anchor = findNewAnchor(prefix, prevAnchors);
				prevAnchors.add(anchor);
				return anchor;
			},
			/**
			* With circular references, the source node is only resolved after all
			* of its child nodes are. This is why anchors are set only after all of
			* the nodes have been created.
			*/
			setAnchors: () => {
				for (const source of aliasObjects) {
					const ref = sourceObjects.get(source);
					if (typeof ref === "object" && ref.anchor && (isScalar(ref.node) || isCollection(ref.node))) ref.node.anchor = ref.anchor;
					else {
						const error = /* @__PURE__ */ new Error("Failed to resolve repeated object (this should not happen)");
						error.source = source;
						throw error;
					}
				}
			},
			sourceObjects
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/doc/applyReviver.js
	/**
	* Applies the JSON.parse reviver algorithm as defined in the ECMA-262 spec,
	* in section 24.5.1.1 "Runtime Semantics: InternalizeJSONProperty" of the
	* 2021 edition: https://tc39.es/ecma262/#sec-json.parse
	*
	* Includes extensions for handling Map and Set objects.
	*/
	function applyReviver(reviver, obj, key, val) {
		if (val && typeof val === "object") {
			if (Array.isArray(val)) for (let i = 0, len = val.length; i < len; ++i) {
				const v0 = val[i];
				const v1 = applyReviver(reviver, val, String(i), v0);
				if (v1 === void 0) delete val[i];
				else if (v1 !== v0) val[i] = v1;
			}
			else if (val instanceof Map) for (const k of Array.from(val.keys())) {
				const v0 = val.get(k);
				const v1 = applyReviver(reviver, val, k, v0);
				if (v1 === void 0) val.delete(k);
				else if (v1 !== v0) val.set(k, v1);
			}
			else if (val instanceof Set) for (const v0 of Array.from(val)) {
				const v1 = applyReviver(reviver, val, v0, v0);
				if (v1 === void 0) val.delete(v0);
				else if (v1 !== v0) {
					val.delete(v0);
					val.add(v1);
				}
			}
			else for (const [k, v0] of Object.entries(val)) {
				const v1 = applyReviver(reviver, val, k, v0);
				if (v1 === void 0) delete val[k];
				else if (v1 !== v0) val[k] = v1;
			}
		}
		return reviver.call(obj, key, val);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/toJS.js
	/**
	* Recursively convert any node or its contents to native JavaScript
	*
	* @param value - The input value
	* @param arg - If `value` defines a `toJSON()` method, use this
	*   as its first argument
	* @param ctx - Conversion context, originally set in Document#toJS(). If
	*   `{ keep: true }` is not set, output should be suitable for JSON
	*   stringification.
	*/
	function toJS(value, arg, ctx) {
		if (Array.isArray(value)) return value.map((v, i) => toJS(v, String(i), ctx));
		if (value && typeof value.toJSON === "function") {
			if (!ctx || !hasAnchor(value)) return value.toJSON(arg, ctx);
			const data = {
				aliasCount: 0,
				count: 1,
				res: void 0
			};
			ctx.anchors.set(value, data);
			ctx.onCreate = (res) => {
				data.res = res;
				delete ctx.onCreate;
			};
			const res = value.toJSON(arg, ctx);
			if (ctx.onCreate) ctx.onCreate(res);
			return res;
		}
		if (typeof value === "bigint" && !ctx?.keep) return Number(value);
		return value;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/Node.js
	var NodeBase = class {
		constructor(type) {
			Object.defineProperty(this, NODE_TYPE, { value: type });
		}
		/** Create a copy of this node.  */
		clone() {
			const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
			if (this.range) copy.range = this.range.slice();
			return copy;
		}
		/** A plain JavaScript representation of this node. */
		toJS(doc, { mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
			if (!isDocument(doc)) throw new TypeError("A document argument is required");
			const ctx = {
				anchors: /* @__PURE__ */ new Map(),
				doc,
				keep: true,
				mapAsMap: mapAsMap === true,
				mapKeyWarned: false,
				maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
			};
			const res = toJS(this, "", ctx);
			if (typeof onAnchor === "function") for (const { count, res } of ctx.anchors.values()) onAnchor(res, count);
			return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/Alias.js
	var Alias = class extends NodeBase {
		constructor(source) {
			super(ALIAS);
			this.source = source;
			Object.defineProperty(this, "tag", { set() {
				throw new Error("Alias nodes cannot have tags");
			} });
		}
		/**
		* Resolve the value of this alias within `doc`, finding the last
		* instance of the `source` anchor before this node.
		*/
		resolve(doc, ctx) {
			let nodes;
			if (ctx?.aliasResolveCache) nodes = ctx.aliasResolveCache;
			else {
				nodes = [];
				visit$1(doc, { Node: (_key, node) => {
					if (isAlias(node) || hasAnchor(node)) nodes.push(node);
				} });
				if (ctx) ctx.aliasResolveCache = nodes;
			}
			let found = void 0;
			for (const node of nodes) {
				if (node === this) break;
				if (node.anchor === this.source) found = node;
			}
			return found;
		}
		toJSON(_arg, ctx) {
			if (!ctx) return { source: this.source };
			const { anchors, doc, maxAliasCount } = ctx;
			const source = this.resolve(doc, ctx);
			if (!source) {
				const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
				throw new ReferenceError(msg);
			}
			let data = anchors.get(source);
			if (!data) {
				toJS(source, null, ctx);
				data = anchors.get(source);
			}
			/* istanbul ignore if */
			if (!data || data.res === void 0) throw new ReferenceError("This should not happen: Alias anchor was not resolved?");
			if (maxAliasCount >= 0) {
				data.count += 1;
				if (data.aliasCount === 0) data.aliasCount = getAliasCount(doc, source, anchors);
				if (data.count * data.aliasCount > maxAliasCount) throw new ReferenceError("Excessive alias count indicates a resource exhaustion attack");
			}
			return data.res;
		}
		toString(ctx, _onComment, _onChompKeep) {
			const src = `*${this.source}`;
			if (ctx) {
				anchorIsValid(this.source);
				if (ctx.options.verifyAliasOrder && !ctx.anchors.has(this.source)) {
					const msg = `Unresolved alias (the anchor must be set before the alias): ${this.source}`;
					throw new Error(msg);
				}
				if (ctx.implicitKey) return `${src} `;
			}
			return src;
		}
	};
	function getAliasCount(doc, node, anchors) {
		if (isAlias(node)) {
			const source = node.resolve(doc);
			const anchor = anchors && source && anchors.get(source);
			return anchor ? anchor.count * anchor.aliasCount : 0;
		} else if (isCollection(node)) {
			let count = 0;
			for (const item of node.items) {
				const c = getAliasCount(doc, item, anchors);
				if (c > count) count = c;
			}
			return count;
		} else if (isPair(node)) {
			const kc = getAliasCount(doc, node.key, anchors);
			const vc = getAliasCount(doc, node.value, anchors);
			return Math.max(kc, vc);
		}
		return 1;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/Scalar.js
	var isScalarValue = (value) => !value || typeof value !== "function" && typeof value !== "object";
	var Scalar = class extends NodeBase {
		constructor(value) {
			super(SCALAR$1);
			this.value = value;
		}
		toJSON(arg, ctx) {
			return ctx?.keep ? this.value : toJS(this.value, arg, ctx);
		}
		toString() {
			return String(this.value);
		}
	};
	Scalar.BLOCK_FOLDED = "BLOCK_FOLDED";
	Scalar.BLOCK_LITERAL = "BLOCK_LITERAL";
	Scalar.PLAIN = "PLAIN";
	Scalar.QUOTE_DOUBLE = "QUOTE_DOUBLE";
	Scalar.QUOTE_SINGLE = "QUOTE_SINGLE";
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/doc/createNode.js
	var defaultTagPrefix = "tag:yaml.org,2002:";
	function findTagObject(value, tagName, tags) {
		if (tagName) {
			const match = tags.filter((t) => t.tag === tagName);
			const tagObj = match.find((t) => !t.format) ?? match[0];
			if (!tagObj) throw new Error(`Tag ${tagName} not found`);
			return tagObj;
		}
		return tags.find((t) => t.identify?.(value) && !t.format);
	}
	function createNode(value, tagName, ctx) {
		if (isDocument(value)) value = value.contents;
		if (isNode(value)) return value;
		if (isPair(value)) {
			const map = ctx.schema[MAP].createNode?.(ctx.schema, null, ctx);
			map.items.push(value);
			return map;
		}
		if (value instanceof String || value instanceof Number || value instanceof Boolean || typeof BigInt !== "undefined" && value instanceof BigInt) value = value.valueOf();
		const { aliasDuplicateObjects, onAnchor, onTagObj, schema, sourceObjects } = ctx;
		let ref = void 0;
		if (aliasDuplicateObjects && value && typeof value === "object") {
			ref = sourceObjects.get(value);
			if (ref) {
				ref.anchor ?? (ref.anchor = onAnchor(value));
				return new Alias(ref.anchor);
			} else {
				ref = {
					anchor: null,
					node: null
				};
				sourceObjects.set(value, ref);
			}
		}
		if (tagName?.startsWith("!!")) tagName = defaultTagPrefix + tagName.slice(2);
		let tagObj = findTagObject(value, tagName, schema.tags);
		if (!tagObj) {
			if (value && typeof value.toJSON === "function") value = value.toJSON();
			if (!value || typeof value !== "object") {
				const node = new Scalar(value);
				if (ref) ref.node = node;
				return node;
			}
			tagObj = value instanceof Map ? schema[MAP] : Symbol.iterator in Object(value) ? schema[SEQ] : schema[MAP];
		}
		if (onTagObj) {
			onTagObj(tagObj);
			delete ctx.onTagObj;
		}
		const node = tagObj?.createNode ? tagObj.createNode(ctx.schema, value, ctx) : typeof tagObj?.nodeClass?.from === "function" ? tagObj.nodeClass.from(ctx.schema, value, ctx) : new Scalar(value);
		if (tagName) node.tag = tagName;
		else if (!tagObj.default) node.tag = tagObj.tag;
		if (ref) ref.node = node;
		return node;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/Collection.js
	function collectionFromPath(schema, path, value) {
		let v = value;
		for (let i = path.length - 1; i >= 0; --i) {
			const k = path[i];
			if (typeof k === "number" && Number.isInteger(k) && k >= 0) {
				const a = [];
				a[k] = v;
				v = a;
			} else v = /* @__PURE__ */ new Map([[k, v]]);
		}
		return createNode(v, void 0, {
			aliasDuplicateObjects: false,
			keepUndefined: false,
			onAnchor: () => {
				throw new Error("This should not happen, please report a bug.");
			},
			schema,
			sourceObjects: /* @__PURE__ */ new Map()
		});
	}
	var isEmptyPath = (path) => path == null || typeof path === "object" && !!path[Symbol.iterator]().next().done;
	var Collection = class extends NodeBase {
		constructor(type, schema) {
			super(type);
			Object.defineProperty(this, "schema", {
				value: schema,
				configurable: true,
				enumerable: false,
				writable: true
			});
		}
		/**
		* Create a copy of this collection.
		*
		* @param schema - If defined, overwrites the original's schema
		*/
		clone(schema) {
			const copy = Object.create(Object.getPrototypeOf(this), Object.getOwnPropertyDescriptors(this));
			if (schema) copy.schema = schema;
			copy.items = copy.items.map((it) => isNode(it) || isPair(it) ? it.clone(schema) : it);
			if (this.range) copy.range = this.range.slice();
			return copy;
		}
		/**
		* Adds a value to the collection. For `!!map` and `!!omap` the value must
		* be a Pair instance or a `{ key, value }` object, which may not have a key
		* that already exists in the map.
		*/
		addIn(path, value) {
			if (isEmptyPath(path)) this.add(value);
			else {
				const [key, ...rest] = path;
				const node = this.get(key, true);
				if (isCollection(node)) node.addIn(rest, value);
				else if (node === void 0 && this.schema) this.set(key, collectionFromPath(this.schema, rest, value));
				else throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
			}
		}
		/**
		* Removes a value from the collection.
		* @returns `true` if the item was found and removed.
		*/
		deleteIn(path) {
			const [key, ...rest] = path;
			if (rest.length === 0) return this.delete(key);
			const node = this.get(key, true);
			if (isCollection(node)) return node.deleteIn(rest);
			else throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
		}
		/**
		* Returns item at `key`, or `undefined` if not found. By default unwraps
		* scalar values from their surrounding node; to disable set `keepScalar` to
		* `true` (collections are always returned intact).
		*/
		getIn(path, keepScalar) {
			const [key, ...rest] = path;
			const node = this.get(key, true);
			if (rest.length === 0) return !keepScalar && isScalar(node) ? node.value : node;
			else return isCollection(node) ? node.getIn(rest, keepScalar) : void 0;
		}
		hasAllNullValues(allowScalar) {
			return this.items.every((node) => {
				if (!isPair(node)) return false;
				const n = node.value;
				return n == null || allowScalar && isScalar(n) && n.value == null && !n.commentBefore && !n.comment && !n.tag;
			});
		}
		/**
		* Checks if the collection includes a value with the key `key`.
		*/
		hasIn(path) {
			const [key, ...rest] = path;
			if (rest.length === 0) return this.has(key);
			const node = this.get(key, true);
			return isCollection(node) ? node.hasIn(rest) : false;
		}
		/**
		* Sets a value in this collection. For `!!set`, `value` needs to be a
		* boolean to add/remove the item from the set.
		*/
		setIn(path, value) {
			const [key, ...rest] = path;
			if (rest.length === 0) this.set(key, value);
			else {
				const node = this.get(key, true);
				if (isCollection(node)) node.setIn(rest, value);
				else if (node === void 0 && this.schema) this.set(key, collectionFromPath(this.schema, rest, value));
				else throw new Error(`Expected YAML collection at ${key}. Remaining path: ${rest}`);
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyComment.js
	/**
	* Stringifies a comment.
	*
	* Empty comment lines are left empty,
	* lines consisting of a single space are replaced by `#`,
	* and all other lines are prefixed with a `#`.
	*/
	var stringifyComment = (str) => str.replace(/^(?!$)(?: $)?/gm, "#");
	function indentComment(comment, indent) {
		if (/^\n+$/.test(comment)) return comment.substring(1);
		return indent ? comment.replace(/^(?! *$)/gm, indent) : comment;
	}
	var lineComment = (str, indent, comment) => str.endsWith("\n") ? indentComment(comment, indent) : comment.includes("\n") ? "\n" + indentComment(comment, indent) : (str.endsWith(" ") ? "" : " ") + comment;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/foldFlowLines.js
	var FOLD_FLOW = "flow";
	var FOLD_BLOCK = "block";
	var FOLD_QUOTED = "quoted";
	/**
	* Tries to keep input at up to `lineWidth` characters, splitting only on spaces
	* not followed by newlines or spaces unless `mode` is `'quoted'`. Lines are
	* terminated with `\n` and started with `indent`.
	*/
	function foldFlowLines(text, indent, mode = "flow", { indentAtStart, lineWidth = 80, minContentWidth = 20, onFold, onOverflow } = {}) {
		if (!lineWidth || lineWidth < 0) return text;
		if (lineWidth < minContentWidth) minContentWidth = 0;
		const endStep = Math.max(1 + minContentWidth, 1 + lineWidth - indent.length);
		if (text.length <= endStep) return text;
		const folds = [];
		const escapedFolds = {};
		let end = lineWidth - indent.length;
		if (typeof indentAtStart === "number") {
			if (indentAtStart > lineWidth - Math.max(2, minContentWidth)) folds.push(0);
			else end = lineWidth - indentAtStart;
		}
		let split = void 0;
		let prev = void 0;
		let overflow = false;
		let i = -1;
		let escStart = -1;
		let escEnd = -1;
		if (mode === "block") {
			i = consumeMoreIndentedLines(text, i, indent.length);
			if (i !== -1) end = i + endStep;
		}
		for (let ch; ch = text[i += 1];) {
			if (mode === "quoted" && ch === "\\") {
				escStart = i;
				switch (text[i + 1]) {
					case "x":
						i += 3;
						break;
					case "u":
						i += 5;
						break;
					case "U":
						i += 9;
						break;
					default: i += 1;
				}
				escEnd = i;
			}
			if (ch === "\n") {
				if (mode === "block") i = consumeMoreIndentedLines(text, i, indent.length);
				end = i + indent.length + endStep;
				split = void 0;
			} else {
				if (ch === " " && prev && prev !== " " && prev !== "\n" && prev !== "	") {
					const next = text[i + 1];
					if (next && next !== " " && next !== "\n" && next !== "	") split = i;
				}
				if (i >= end) {
					if (split) {
						folds.push(split);
						end = split + endStep;
						split = void 0;
					} else if (mode === "quoted") {
						while (prev === " " || prev === "	") {
							prev = ch;
							ch = text[i += 1];
							overflow = true;
						}
						const j = i > escEnd + 1 ? i - 2 : escStart - 1;
						if (escapedFolds[j]) return text;
						folds.push(j);
						escapedFolds[j] = true;
						end = j + endStep;
						split = void 0;
					} else overflow = true;
				}
			}
			prev = ch;
		}
		if (overflow && onOverflow) onOverflow();
		if (folds.length === 0) return text;
		if (onFold) onFold();
		let res = text.slice(0, folds[0]);
		for (let i = 0; i < folds.length; ++i) {
			const fold = folds[i];
			const end = folds[i + 1] || text.length;
			if (fold === 0) res = `\n${indent}${text.slice(0, end)}`;
			else {
				if (mode === "quoted" && escapedFolds[fold]) res += `${text[fold]}\\`;
				res += `\n${indent}${text.slice(fold + 1, end)}`;
			}
		}
		return res;
	}
	/**
	* Presumes `i + 1` is at the start of a line
	* @returns index of last newline in more-indented block
	*/
	function consumeMoreIndentedLines(text, i, indent) {
		let end = i;
		let start = i + 1;
		let ch = text[start];
		while (ch === " " || ch === "	") if (i < start + indent) ch = text[++i];
		else {
			do
				ch = text[++i];
			while (ch && ch !== "\n");
			end = i;
			start = i + 1;
			ch = text[start];
		}
		return end;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyString.js
	var getFoldOptions = (ctx, isBlock) => ({
		indentAtStart: isBlock ? ctx.indent.length : ctx.indentAtStart,
		lineWidth: ctx.options.lineWidth,
		minContentWidth: ctx.options.minContentWidth
	});
	var containsDocumentMarker = (str) => /^(%|---|\.\.\.)/m.test(str);
	function lineLengthOverLimit(str, lineWidth, indentLength) {
		if (!lineWidth || lineWidth < 0) return false;
		const limit = lineWidth - indentLength;
		const strLen = str.length;
		if (strLen <= limit) return false;
		for (let i = 0, start = 0; i < strLen; ++i) if (str[i] === "\n") {
			if (i - start > limit) return true;
			start = i + 1;
			if (strLen - start <= limit) return false;
		}
		return true;
	}
	function doubleQuotedString(value, ctx) {
		const json = JSON.stringify(value);
		if (ctx.options.doubleQuotedAsJSON) return json;
		const { implicitKey } = ctx;
		const minMultiLineLength = ctx.options.doubleQuotedMinMultiLineLength;
		const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
		let str = "";
		let start = 0;
		for (let i = 0, ch = json[i]; ch; ch = json[++i]) {
			if (ch === " " && json[i + 1] === "\\" && json[i + 2] === "n") {
				str += json.slice(start, i) + "\\ ";
				i += 1;
				start = i;
				ch = "\\";
			}
			if (ch === "\\") switch (json[i + 1]) {
				case "u":
					{
						str += json.slice(start, i);
						const code = json.substr(i + 2, 4);
						switch (code) {
							case "0000":
								str += "\\0";
								break;
							case "0007":
								str += "\\a";
								break;
							case "000b":
								str += "\\v";
								break;
							case "001b":
								str += "\\e";
								break;
							case "0085":
								str += "\\N";
								break;
							case "00a0":
								str += "\\_";
								break;
							case "2028":
								str += "\\L";
								break;
							case "2029":
								str += "\\P";
								break;
							default: if (code.substr(0, 2) === "00") str += "\\x" + code.substr(2);
							else str += json.substr(i, 6);
						}
						i += 5;
						start = i + 1;
					}
					break;
				case "n":
					if (implicitKey || json[i + 2] === "\"" || json.length < minMultiLineLength) i += 1;
					else {
						str += json.slice(start, i) + "\n\n";
						while (json[i + 2] === "\\" && json[i + 3] === "n" && json[i + 4] !== "\"") {
							str += "\n";
							i += 2;
						}
						str += indent;
						if (json[i + 2] === " ") str += "\\";
						i += 1;
						start = i + 1;
					}
					break;
				default: i += 1;
			}
		}
		str = start ? str + json.slice(start) : json;
		return implicitKey ? str : foldFlowLines(str, indent, FOLD_QUOTED, getFoldOptions(ctx, false));
	}
	function singleQuotedString(value, ctx) {
		if (ctx.options.singleQuote === false || ctx.implicitKey && value.includes("\n") || /[ \t]\n|\n[ \t]/.test(value)) return doubleQuotedString(value, ctx);
		const indent = ctx.indent || (containsDocumentMarker(value) ? "  " : "");
		const res = "'" + value.replace(/'/g, "''").replace(/\n+/g, `$&\n${indent}`) + "'";
		return ctx.implicitKey ? res : foldFlowLines(res, indent, FOLD_FLOW, getFoldOptions(ctx, false));
	}
	function quotedString(value, ctx) {
		const { singleQuote } = ctx.options;
		let qs;
		if (singleQuote === false) qs = doubleQuotedString;
		else {
			const hasDouble = value.includes("\"");
			const hasSingle = value.includes("'");
			if (hasDouble && !hasSingle) qs = singleQuotedString;
			else if (hasSingle && !hasDouble) qs = doubleQuotedString;
			else qs = singleQuote ? singleQuotedString : doubleQuotedString;
		}
		return qs(value, ctx);
	}
	var blockEndNewlines;
	try {
		blockEndNewlines = /* @__PURE__ */ new RegExp("(^|(?<!\n))\n+(?!\n|$)", "g");
	} catch {
		blockEndNewlines = /\n+(?!\n|$)/g;
	}
	function blockString({ comment, type, value }, ctx, onComment, onChompKeep) {
		const { blockQuote, commentString, lineWidth } = ctx.options;
		if (!blockQuote || /\n[\t ]+$/.test(value)) return quotedString(value, ctx);
		const indent = ctx.indent || (ctx.forceBlockIndent || containsDocumentMarker(value) ? "  " : "");
		const literal = blockQuote === "literal" ? true : blockQuote === "folded" || type === Scalar.BLOCK_FOLDED ? false : type === Scalar.BLOCK_LITERAL ? true : !lineLengthOverLimit(value, lineWidth, indent.length);
		if (!value) return literal ? "|\n" : ">\n";
		let chomp;
		let endStart;
		for (endStart = value.length; endStart > 0; --endStart) {
			const ch = value[endStart - 1];
			if (ch !== "\n" && ch !== "	" && ch !== " ") break;
		}
		let end = value.substring(endStart);
		const endNlPos = end.indexOf("\n");
		if (endNlPos === -1) chomp = "-";
		else if (value === end || endNlPos !== end.length - 1) {
			chomp = "+";
			if (onChompKeep) onChompKeep();
		} else chomp = "";
		if (end) {
			value = value.slice(0, -end.length);
			if (end[end.length - 1] === "\n") end = end.slice(0, -1);
			end = end.replace(blockEndNewlines, `$&${indent}`);
		}
		let startWithSpace = false;
		let startEnd;
		let startNlPos = -1;
		for (startEnd = 0; startEnd < value.length; ++startEnd) {
			const ch = value[startEnd];
			if (ch === " ") startWithSpace = true;
			else if (ch === "\n") startNlPos = startEnd;
			else break;
		}
		let start = value.substring(0, startNlPos < startEnd ? startNlPos + 1 : startEnd);
		if (start) {
			value = value.substring(start.length);
			start = start.replace(/\n+/g, `$&${indent}`);
		}
		let header = (startWithSpace ? indent ? "2" : "1" : "") + chomp;
		if (comment) {
			header += " " + commentString(comment.replace(/ ?[\r\n]+/g, " "));
			if (onComment) onComment();
		}
		if (!literal) {
			const foldedValue = value.replace(/\n+/g, "\n$&").replace(/(?:^|\n)([\t ].*)(?:([\n\t ]*)\n(?![\n\t ]))?/g, "$1$2").replace(/\n+/g, `$&${indent}`);
			let literalFallback = false;
			const foldOptions = getFoldOptions(ctx, true);
			if (blockQuote !== "folded" && type !== Scalar.BLOCK_FOLDED) foldOptions.onOverflow = () => {
				literalFallback = true;
			};
			const body = foldFlowLines(`${start}${foldedValue}${end}`, indent, FOLD_BLOCK, foldOptions);
			if (!literalFallback) return `>${header}\n${indent}${body}`;
		}
		value = value.replace(/\n+/g, `$&${indent}`);
		return `|${header}\n${indent}${start}${value}${end}`;
	}
	function plainString(item, ctx, onComment, onChompKeep) {
		const { type, value } = item;
		const { actualString, implicitKey, indent, indentStep, inFlow } = ctx;
		if (implicitKey && value.includes("\n") || inFlow && /[[\]{},]/.test(value)) return quotedString(value, ctx);
		if (/^[\n\t ,[\]{}#&*!|>'"%@`]|^[?-]$|^[?-][ \t]|[\n:][ \t]|[ \t]\n|[\n\t ]#|[\n\t :]$/.test(value)) return implicitKey || inFlow || !value.includes("\n") ? quotedString(value, ctx) : blockString(item, ctx, onComment, onChompKeep);
		if (!implicitKey && !inFlow && type !== Scalar.PLAIN && value.includes("\n")) return blockString(item, ctx, onComment, onChompKeep);
		if (containsDocumentMarker(value)) {
			if (indent === "") {
				ctx.forceBlockIndent = true;
				return blockString(item, ctx, onComment, onChompKeep);
			} else if (implicitKey && indent === indentStep) return quotedString(value, ctx);
		}
		const str = value.replace(/\n+/g, `$&\n${indent}`);
		if (actualString) {
			const test = (tag) => tag.default && tag.tag !== "tag:yaml.org,2002:str" && tag.test?.test(str);
			const { compat, tags } = ctx.doc.schema;
			if (tags.some(test) || compat?.some(test)) return quotedString(value, ctx);
		}
		return implicitKey ? str : foldFlowLines(str, indent, FOLD_FLOW, getFoldOptions(ctx, false));
	}
	function stringifyString(item, ctx, onComment, onChompKeep) {
		const { implicitKey, inFlow } = ctx;
		const ss = typeof item.value === "string" ? item : Object.assign({}, item, { value: String(item.value) });
		let { type } = item;
		if (type !== Scalar.QUOTE_DOUBLE) {
			if (/[\x00-\x08\x0b-\x1f\x7f-\x9f\u{D800}-\u{DFFF}]/u.test(ss.value)) type = Scalar.QUOTE_DOUBLE;
		}
		const _stringify = (_type) => {
			switch (_type) {
				case Scalar.BLOCK_FOLDED:
				case Scalar.BLOCK_LITERAL: return implicitKey || inFlow ? quotedString(ss.value, ctx) : blockString(ss, ctx, onComment, onChompKeep);
				case Scalar.QUOTE_DOUBLE: return doubleQuotedString(ss.value, ctx);
				case Scalar.QUOTE_SINGLE: return singleQuotedString(ss.value, ctx);
				case Scalar.PLAIN: return plainString(ss, ctx, onComment, onChompKeep);
				default: return null;
			}
		};
		let res = _stringify(type);
		if (res === null) {
			const { defaultKeyType, defaultStringType } = ctx.options;
			const t = implicitKey && defaultKeyType || defaultStringType;
			res = _stringify(t);
			if (res === null) throw new Error(`Unsupported default string type ${t}`);
		}
		return res;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringify.js
	function createStringifyContext(doc, options) {
		const opt = Object.assign({
			blockQuote: true,
			commentString: stringifyComment,
			defaultKeyType: null,
			defaultStringType: "PLAIN",
			directives: null,
			doubleQuotedAsJSON: false,
			doubleQuotedMinMultiLineLength: 40,
			falseStr: "false",
			flowCollectionPadding: true,
			indentSeq: true,
			lineWidth: 80,
			minContentWidth: 20,
			nullStr: "null",
			simpleKeys: false,
			singleQuote: null,
			trueStr: "true",
			verifyAliasOrder: true
		}, doc.schema.toStringOptions, options);
		let inFlow;
		switch (opt.collectionStyle) {
			case "block":
				inFlow = false;
				break;
			case "flow":
				inFlow = true;
				break;
			default: inFlow = null;
		}
		return {
			anchors: /* @__PURE__ */ new Set(),
			doc,
			flowCollectionPadding: opt.flowCollectionPadding ? " " : "",
			indent: "",
			indentStep: typeof opt.indent === "number" ? " ".repeat(opt.indent) : "  ",
			inFlow,
			options: opt
		};
	}
	function getTagObject(tags, item) {
		if (item.tag) {
			const match = tags.filter((t) => t.tag === item.tag);
			if (match.length > 0) return match.find((t) => t.format === item.format) ?? match[0];
		}
		let tagObj = void 0;
		let obj;
		if (isScalar(item)) {
			obj = item.value;
			let match = tags.filter((t) => t.identify?.(obj));
			if (match.length > 1) {
				const testMatch = match.filter((t) => t.test);
				if (testMatch.length > 0) match = testMatch;
			}
			tagObj = match.find((t) => t.format === item.format) ?? match.find((t) => !t.format);
		} else {
			obj = item;
			tagObj = tags.find((t) => t.nodeClass && obj instanceof t.nodeClass);
		}
		if (!tagObj) {
			const name = obj?.constructor?.name ?? (obj === null ? "null" : typeof obj);
			throw new Error(`Tag not resolved for ${name} value`);
		}
		return tagObj;
	}
	function stringifyProps(node, tagObj, { anchors, doc }) {
		if (!doc.directives) return "";
		const props = [];
		const anchor = (isScalar(node) || isCollection(node)) && node.anchor;
		if (anchor && anchorIsValid(anchor)) {
			anchors.add(anchor);
			props.push(`&${anchor}`);
		}
		const tag = node.tag ?? (tagObj.default ? null : tagObj.tag);
		if (tag) props.push(doc.directives.tagString(tag));
		return props.join(" ");
	}
	function stringify(item, ctx, onComment, onChompKeep) {
		if (isPair(item)) return item.toString(ctx, onComment, onChompKeep);
		if (isAlias(item)) {
			if (ctx.doc.directives) return item.toString(ctx);
			if (ctx.resolvedAliases?.has(item)) throw new TypeError(`Cannot stringify circular structure without alias nodes`);
			else {
				if (ctx.resolvedAliases) ctx.resolvedAliases.add(item);
				else ctx.resolvedAliases = /* @__PURE__ */ new Set([item]);
				item = item.resolve(ctx.doc);
			}
		}
		let tagObj = void 0;
		const node = isNode(item) ? item : ctx.doc.createNode(item, { onTagObj: (o) => tagObj = o });
		tagObj ?? (tagObj = getTagObject(ctx.doc.schema.tags, node));
		const props = stringifyProps(node, tagObj, ctx);
		if (props.length > 0) ctx.indentAtStart = (ctx.indentAtStart ?? 0) + props.length + 1;
		const str = typeof tagObj.stringify === "function" ? tagObj.stringify(node, ctx, onComment, onChompKeep) : isScalar(node) ? stringifyString(node, ctx, onComment, onChompKeep) : node.toString(ctx, onComment, onChompKeep);
		if (!props) return str;
		return isScalar(node) || str[0] === "{" || str[0] === "[" ? `${props} ${str}` : `${props}\n${ctx.indent}${str}`;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyPair.js
	function stringifyPair({ key, value }, ctx, onComment, onChompKeep) {
		const { allNullValues, doc, indent, indentStep, options: { commentString, indentSeq, simpleKeys } } = ctx;
		let keyComment = isNode(key) && key.comment || null;
		if (simpleKeys) {
			if (keyComment) throw new Error("With simple keys, key nodes cannot have comments");
			if (isCollection(key) || !isNode(key) && typeof key === "object") throw new Error("With simple keys, collection cannot be used as a key value");
		}
		let explicitKey = !simpleKeys && (!key || keyComment && value == null && !ctx.inFlow || isCollection(key) || (isScalar(key) ? key.type === Scalar.BLOCK_FOLDED || key.type === Scalar.BLOCK_LITERAL : typeof key === "object"));
		ctx = Object.assign({}, ctx, {
			allNullValues: false,
			implicitKey: !explicitKey && (simpleKeys || !allNullValues),
			indent: indent + indentStep
		});
		let keyCommentDone = false;
		let chompKeep = false;
		let str = stringify(key, ctx, () => keyCommentDone = true, () => chompKeep = true);
		if (!explicitKey && !ctx.inFlow && str.length > 1024) {
			if (simpleKeys) throw new Error("With simple keys, single line scalar must not span more than 1024 characters");
			explicitKey = true;
		}
		if (ctx.inFlow) {
			if (allNullValues || value == null) {
				if (keyCommentDone && onComment) onComment();
				return str === "" ? "?" : explicitKey ? `? ${str}` : str;
			}
		} else if (allNullValues && !simpleKeys || value == null && explicitKey) {
			str = `? ${str}`;
			if (keyComment && !keyCommentDone) str += lineComment(str, ctx.indent, commentString(keyComment));
			else if (chompKeep && onChompKeep) onChompKeep();
			return str;
		}
		if (keyCommentDone) keyComment = null;
		if (explicitKey) {
			if (keyComment) str += lineComment(str, ctx.indent, commentString(keyComment));
			str = `? ${str}\n${indent}:`;
		} else {
			str = `${str}:`;
			if (keyComment) str += lineComment(str, ctx.indent, commentString(keyComment));
		}
		let vsb, vcb, valueComment;
		if (isNode(value)) {
			vsb = !!value.spaceBefore;
			vcb = value.commentBefore;
			valueComment = value.comment;
		} else {
			vsb = false;
			vcb = null;
			valueComment = null;
			if (value && typeof value === "object") value = doc.createNode(value);
		}
		ctx.implicitKey = false;
		if (!explicitKey && !keyComment && isScalar(value)) ctx.indentAtStart = str.length + 1;
		chompKeep = false;
		if (!indentSeq && indentStep.length >= 2 && !ctx.inFlow && !explicitKey && isSeq(value) && !value.flow && !value.tag && !value.anchor) ctx.indent = ctx.indent.substring(2);
		let valueCommentDone = false;
		const valueStr = stringify(value, ctx, () => valueCommentDone = true, () => chompKeep = true);
		let ws = " ";
		if (keyComment || vsb || vcb) {
			ws = vsb ? "\n" : "";
			if (vcb) {
				const cs = commentString(vcb);
				ws += `\n${indentComment(cs, ctx.indent)}`;
			}
			if (valueStr === "" && !ctx.inFlow) {
				if (ws === "\n") ws = "\n\n";
			} else ws += `\n${ctx.indent}`;
		} else if (!explicitKey && isCollection(value)) {
			const vs0 = valueStr[0];
			const nl0 = valueStr.indexOf("\n");
			const hasNewline = nl0 !== -1;
			const flow = ctx.inFlow ?? value.flow ?? value.items.length === 0;
			if (hasNewline || !flow) {
				let hasPropsLine = false;
				if (hasNewline && (vs0 === "&" || vs0 === "!")) {
					let sp0 = valueStr.indexOf(" ");
					if (vs0 === "&" && sp0 !== -1 && sp0 < nl0 && valueStr[sp0 + 1] === "!") sp0 = valueStr.indexOf(" ", sp0 + 1);
					if (sp0 === -1 || nl0 < sp0) hasPropsLine = true;
				}
				if (!hasPropsLine) ws = `\n${ctx.indent}`;
			}
		} else if (valueStr === "" || valueStr[0] === "\n") ws = "";
		str += ws + valueStr;
		if (ctx.inFlow) {
			if (valueCommentDone && onComment) onComment();
		} else if (valueComment && !valueCommentDone) str += lineComment(str, ctx.indent, commentString(valueComment));
		else if (chompKeep && onChompKeep) onChompKeep();
		return str;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/log.js
	function warn(logLevel, warning) {
		if (logLevel === "debug" || logLevel === "warn") console.warn(warning);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/merge.js
	var MERGE_KEY = "<<";
	var merge = {
		identify: (value) => value === MERGE_KEY || typeof value === "symbol" && value.description === MERGE_KEY,
		default: "key",
		tag: "tag:yaml.org,2002:merge",
		test: /^<<$/,
		resolve: () => Object.assign(new Scalar(Symbol(MERGE_KEY)), { addToJSMap: addMergeToJSMap }),
		stringify: () => MERGE_KEY
	};
	var isMergeKey = (ctx, key) => (merge.identify(key) || isScalar(key) && (!key.type || key.type === Scalar.PLAIN) && merge.identify(key.value)) && ctx?.doc.schema.tags.some((tag) => tag.tag === merge.tag && tag.default);
	function addMergeToJSMap(ctx, map, value) {
		value = ctx && isAlias(value) ? value.resolve(ctx.doc) : value;
		if (isSeq(value)) for (const it of value.items) mergeValue(ctx, map, it);
		else if (Array.isArray(value)) for (const it of value) mergeValue(ctx, map, it);
		else mergeValue(ctx, map, value);
	}
	function mergeValue(ctx, map, value) {
		const source = ctx && isAlias(value) ? value.resolve(ctx.doc) : value;
		if (!isMap(source)) throw new Error("Merge sources must be maps or map aliases");
		const srcMap = source.toJSON(null, ctx, Map);
		for (const [key, value] of srcMap) if (map instanceof Map) {
			if (!map.has(key)) map.set(key, value);
		} else if (map instanceof Set) map.add(key);
		else if (!Object.prototype.hasOwnProperty.call(map, key)) Object.defineProperty(map, key, {
			value,
			writable: true,
			enumerable: true,
			configurable: true
		});
		return map;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/addPairToJSMap.js
	function addPairToJSMap(ctx, map, { key, value }) {
		if (isNode(key) && key.addToJSMap) key.addToJSMap(ctx, map, value);
		else if (isMergeKey(ctx, key)) addMergeToJSMap(ctx, map, value);
		else {
			const jsKey = toJS(key, "", ctx);
			if (map instanceof Map) map.set(jsKey, toJS(value, jsKey, ctx));
			else if (map instanceof Set) map.add(jsKey);
			else {
				const stringKey = stringifyKey(key, jsKey, ctx);
				const jsValue = toJS(value, stringKey, ctx);
				if (stringKey in map) Object.defineProperty(map, stringKey, {
					value: jsValue,
					writable: true,
					enumerable: true,
					configurable: true
				});
				else map[stringKey] = jsValue;
			}
		}
		return map;
	}
	function stringifyKey(key, jsKey, ctx) {
		if (jsKey === null) return "";
		if (typeof jsKey !== "object") return String(jsKey);
		if (isNode(key) && ctx?.doc) {
			const strCtx = createStringifyContext(ctx.doc, {});
			strCtx.anchors = /* @__PURE__ */ new Set();
			for (const node of ctx.anchors.keys()) strCtx.anchors.add(node.anchor);
			strCtx.inFlow = true;
			strCtx.inStringifyKey = true;
			const strKey = key.toString(strCtx);
			if (!ctx.mapKeyWarned) {
				let jsonStr = JSON.stringify(strKey);
				if (jsonStr.length > 40) jsonStr = jsonStr.substring(0, 36) + "...\"";
				warn(ctx.doc.options.logLevel, `Keys with collection values will be stringified due to JS Object restrictions: ${jsonStr}. Set mapAsMap: true to use object keys.`);
				ctx.mapKeyWarned = true;
			}
			return strKey;
		}
		return JSON.stringify(jsKey);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/Pair.js
	function createPair(key, value, ctx) {
		return new Pair(createNode(key, void 0, ctx), createNode(value, void 0, ctx));
	}
	var Pair = class Pair {
		constructor(key, value = null) {
			Object.defineProperty(this, NODE_TYPE, { value: PAIR });
			this.key = key;
			this.value = value;
		}
		clone(schema) {
			let { key, value } = this;
			if (isNode(key)) key = key.clone(schema);
			if (isNode(value)) value = value.clone(schema);
			return new Pair(key, value);
		}
		toJSON(_, ctx) {
			return addPairToJSMap(ctx, ctx?.mapAsMap ? /* @__PURE__ */ new Map() : {}, this);
		}
		toString(ctx, onComment, onChompKeep) {
			return ctx?.doc ? stringifyPair(this, ctx, onComment, onChompKeep) : JSON.stringify(this);
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyCollection.js
	function stringifyCollection(collection, ctx, options) {
		return (ctx.inFlow ?? collection.flow ? stringifyFlowCollection : stringifyBlockCollection)(collection, ctx, options);
	}
	function stringifyBlockCollection({ comment, items }, ctx, { blockItemPrefix, flowChars, itemIndent, onChompKeep, onComment }) {
		const { indent, options: { commentString } } = ctx;
		const itemCtx = Object.assign({}, ctx, {
			indent: itemIndent,
			type: null
		});
		let chompKeep = false;
		const lines = [];
		for (let i = 0; i < items.length; ++i) {
			const item = items[i];
			let comment = null;
			if (isNode(item)) {
				if (!chompKeep && item.spaceBefore) lines.push("");
				addCommentBefore(ctx, lines, item.commentBefore, chompKeep);
				if (item.comment) comment = item.comment;
			} else if (isPair(item)) {
				const ik = isNode(item.key) ? item.key : null;
				if (ik) {
					if (!chompKeep && ik.spaceBefore) lines.push("");
					addCommentBefore(ctx, lines, ik.commentBefore, chompKeep);
				}
			}
			chompKeep = false;
			let str = stringify(item, itemCtx, () => comment = null, () => chompKeep = true);
			if (comment) str += lineComment(str, itemIndent, commentString(comment));
			if (chompKeep && comment) chompKeep = false;
			lines.push(blockItemPrefix + str);
		}
		let str;
		if (lines.length === 0) str = flowChars.start + flowChars.end;
		else {
			str = lines[0];
			for (let i = 1; i < lines.length; ++i) {
				const line = lines[i];
				str += line ? `\n${indent}${line}` : "\n";
			}
		}
		if (comment) {
			str += "\n" + indentComment(commentString(comment), indent);
			if (onComment) onComment();
		} else if (chompKeep && onChompKeep) onChompKeep();
		return str;
	}
	function stringifyFlowCollection({ items }, ctx, { flowChars, itemIndent }) {
		const { indent, indentStep, flowCollectionPadding: fcPadding, options: { commentString } } = ctx;
		itemIndent += indentStep;
		const itemCtx = Object.assign({}, ctx, {
			indent: itemIndent,
			inFlow: true,
			type: null
		});
		let reqNewline = false;
		let linesAtValue = 0;
		const lines = [];
		for (let i = 0; i < items.length; ++i) {
			const item = items[i];
			let comment = null;
			if (isNode(item)) {
				if (item.spaceBefore) lines.push("");
				addCommentBefore(ctx, lines, item.commentBefore, false);
				if (item.comment) comment = item.comment;
			} else if (isPair(item)) {
				const ik = isNode(item.key) ? item.key : null;
				if (ik) {
					if (ik.spaceBefore) lines.push("");
					addCommentBefore(ctx, lines, ik.commentBefore, false);
					if (ik.comment) reqNewline = true;
				}
				const iv = isNode(item.value) ? item.value : null;
				if (iv) {
					if (iv.comment) comment = iv.comment;
					if (iv.commentBefore) reqNewline = true;
				} else if (item.value == null && ik?.comment) comment = ik.comment;
			}
			if (comment) reqNewline = true;
			let str = stringify(item, itemCtx, () => comment = null);
			if (i < items.length - 1) str += ",";
			if (comment) str += lineComment(str, itemIndent, commentString(comment));
			if (!reqNewline && (lines.length > linesAtValue || str.includes("\n"))) reqNewline = true;
			lines.push(str);
			linesAtValue = lines.length;
		}
		const { start, end } = flowChars;
		if (lines.length === 0) return start + end;
		else {
			if (!reqNewline) {
				const len = lines.reduce((sum, line) => sum + line.length + 2, 2);
				reqNewline = ctx.options.lineWidth > 0 && len > ctx.options.lineWidth;
			}
			if (reqNewline) {
				let str = start;
				for (const line of lines) str += line ? `\n${indentStep}${indent}${line}` : "\n";
				return `${str}\n${indent}${end}`;
			} else return `${start}${fcPadding}${lines.join(" ")}${fcPadding}${end}`;
		}
	}
	function addCommentBefore({ indent, options: { commentString } }, lines, comment, chompKeep) {
		if (comment && chompKeep) comment = comment.replace(/^\n+/, "");
		if (comment) {
			const ic = indentComment(commentString(comment), indent);
			lines.push(ic.trimStart());
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/YAMLMap.js
	function findPair(items, key) {
		const k = isScalar(key) ? key.value : key;
		for (const it of items) if (isPair(it)) {
			if (it.key === key || it.key === k) return it;
			if (isScalar(it.key) && it.key.value === k) return it;
		}
	}
	var YAMLMap = class extends Collection {
		static get tagName() {
			return "tag:yaml.org,2002:map";
		}
		constructor(schema) {
			super(MAP, schema);
			this.items = [];
		}
		/**
		* A generic collection parsing method that can be extended
		* to other node classes that inherit from YAMLMap
		*/
		static from(schema, obj, ctx) {
			const { keepUndefined, replacer } = ctx;
			const map = new this(schema);
			const add = (key, value) => {
				if (typeof replacer === "function") value = replacer.call(obj, key, value);
				else if (Array.isArray(replacer) && !replacer.includes(key)) return;
				if (value !== void 0 || keepUndefined) map.items.push(createPair(key, value, ctx));
			};
			if (obj instanceof Map) for (const [key, value] of obj) add(key, value);
			else if (obj && typeof obj === "object") for (const key of Object.keys(obj)) add(key, obj[key]);
			if (typeof schema.sortMapEntries === "function") map.items.sort(schema.sortMapEntries);
			return map;
		}
		/**
		* Adds a value to the collection.
		*
		* @param overwrite - If not set `true`, using a key that is already in the
		*   collection will throw. Otherwise, overwrites the previous value.
		*/
		add(pair, overwrite) {
			let _pair;
			if (isPair(pair)) _pair = pair;
			else if (!pair || typeof pair !== "object" || !("key" in pair)) _pair = new Pair(pair, pair?.value);
			else _pair = new Pair(pair.key, pair.value);
			const prev = findPair(this.items, _pair.key);
			const sortEntries = this.schema?.sortMapEntries;
			if (prev) {
				if (!overwrite) throw new Error(`Key ${_pair.key} already set`);
				if (isScalar(prev.value) && isScalarValue(_pair.value)) prev.value.value = _pair.value;
				else prev.value = _pair.value;
			} else if (sortEntries) {
				const i = this.items.findIndex((item) => sortEntries(_pair, item) < 0);
				if (i === -1) this.items.push(_pair);
				else this.items.splice(i, 0, _pair);
			} else this.items.push(_pair);
		}
		delete(key) {
			const it = findPair(this.items, key);
			if (!it) return false;
			return this.items.splice(this.items.indexOf(it), 1).length > 0;
		}
		get(key, keepScalar) {
			const node = findPair(this.items, key)?.value;
			return (!keepScalar && isScalar(node) ? node.value : node) ?? void 0;
		}
		has(key) {
			return !!findPair(this.items, key);
		}
		set(key, value) {
			this.add(new Pair(key, value), true);
		}
		/**
		* @param ctx - Conversion context, originally set in Document#toJS()
		* @param {Class} Type - If set, forces the returned collection type
		* @returns Instance of Type, Map, or Object
		*/
		toJSON(_, ctx, Type) {
			const map = Type ? new Type() : ctx?.mapAsMap ? /* @__PURE__ */ new Map() : {};
			if (ctx?.onCreate) ctx.onCreate(map);
			for (const item of this.items) addPairToJSMap(ctx, map, item);
			return map;
		}
		toString(ctx, onComment, onChompKeep) {
			if (!ctx) return JSON.stringify(this);
			for (const item of this.items) if (!isPair(item)) throw new Error(`Map items must all be pairs; found ${JSON.stringify(item)} instead`);
			if (!ctx.allNullValues && this.hasAllNullValues(false)) ctx = Object.assign({}, ctx, { allNullValues: true });
			return stringifyCollection(this, ctx, {
				blockItemPrefix: "",
				flowChars: {
					start: "{",
					end: "}"
				},
				itemIndent: ctx.indent || "",
				onChompKeep,
				onComment
			});
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/common/map.js
	var map = {
		collection: "map",
		default: true,
		nodeClass: YAMLMap,
		tag: "tag:yaml.org,2002:map",
		resolve(map, onError) {
			if (!isMap(map)) onError("Expected a mapping for this tag");
			return map;
		},
		createNode: (schema, obj, ctx) => YAMLMap.from(schema, obj, ctx)
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/nodes/YAMLSeq.js
	var YAMLSeq = class extends Collection {
		static get tagName() {
			return "tag:yaml.org,2002:seq";
		}
		constructor(schema) {
			super(SEQ, schema);
			this.items = [];
		}
		add(value) {
			this.items.push(value);
		}
		/**
		* Removes a value from the collection.
		*
		* `key` must contain a representation of an integer for this to succeed.
		* It may be wrapped in a `Scalar`.
		*
		* @returns `true` if the item was found and removed.
		*/
		delete(key) {
			const idx = asItemIndex(key);
			if (typeof idx !== "number") return false;
			return this.items.splice(idx, 1).length > 0;
		}
		get(key, keepScalar) {
			const idx = asItemIndex(key);
			if (typeof idx !== "number") return void 0;
			const it = this.items[idx];
			return !keepScalar && isScalar(it) ? it.value : it;
		}
		/**
		* Checks if the collection includes a value with the key `key`.
		*
		* `key` must contain a representation of an integer for this to succeed.
		* It may be wrapped in a `Scalar`.
		*/
		has(key) {
			const idx = asItemIndex(key);
			return typeof idx === "number" && idx < this.items.length;
		}
		/**
		* Sets a value in this collection. For `!!set`, `value` needs to be a
		* boolean to add/remove the item from the set.
		*
		* If `key` does not contain a representation of an integer, this will throw.
		* It may be wrapped in a `Scalar`.
		*/
		set(key, value) {
			const idx = asItemIndex(key);
			if (typeof idx !== "number") throw new Error(`Expected a valid index, not ${key}.`);
			const prev = this.items[idx];
			if (isScalar(prev) && isScalarValue(value)) prev.value = value;
			else this.items[idx] = value;
		}
		toJSON(_, ctx) {
			const seq = [];
			if (ctx?.onCreate) ctx.onCreate(seq);
			let i = 0;
			for (const item of this.items) seq.push(toJS(item, String(i++), ctx));
			return seq;
		}
		toString(ctx, onComment, onChompKeep) {
			if (!ctx) return JSON.stringify(this);
			return stringifyCollection(this, ctx, {
				blockItemPrefix: "- ",
				flowChars: {
					start: "[",
					end: "]"
				},
				itemIndent: (ctx.indent || "") + "  ",
				onChompKeep,
				onComment
			});
		}
		static from(schema, obj, ctx) {
			const { replacer } = ctx;
			const seq = new this(schema);
			if (obj && Symbol.iterator in Object(obj)) {
				let i = 0;
				for (let it of obj) {
					if (typeof replacer === "function") {
						const key = obj instanceof Set ? it : String(i++);
						it = replacer.call(obj, key, it);
					}
					seq.items.push(createNode(it, void 0, ctx));
				}
			}
			return seq;
		}
	};
	function asItemIndex(key) {
		let idx = isScalar(key) ? key.value : key;
		if (idx && typeof idx === "string") idx = Number(idx);
		return typeof idx === "number" && Number.isInteger(idx) && idx >= 0 ? idx : null;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/common/seq.js
	var seq = {
		collection: "seq",
		default: true,
		nodeClass: YAMLSeq,
		tag: "tag:yaml.org,2002:seq",
		resolve(seq, onError) {
			if (!isSeq(seq)) onError("Expected a sequence for this tag");
			return seq;
		},
		createNode: (schema, obj, ctx) => YAMLSeq.from(schema, obj, ctx)
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/common/string.js
	var string = {
		identify: (value) => typeof value === "string",
		default: true,
		tag: "tag:yaml.org,2002:str",
		resolve: (str) => str,
		stringify(item, ctx, onComment, onChompKeep) {
			ctx = Object.assign({ actualString: true }, ctx);
			return stringifyString(item, ctx, onComment, onChompKeep);
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/common/null.js
	var nullTag = {
		identify: (value) => value == null,
		createNode: () => new Scalar(null),
		default: true,
		tag: "tag:yaml.org,2002:null",
		test: /^(?:~|[Nn]ull|NULL)?$/,
		resolve: () => new Scalar(null),
		stringify: ({ source }, ctx) => typeof source === "string" && nullTag.test.test(source) ? source : ctx.options.nullStr
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/core/bool.js
	var boolTag = {
		identify: (value) => typeof value === "boolean",
		default: true,
		tag: "tag:yaml.org,2002:bool",
		test: /^(?:[Tt]rue|TRUE|[Ff]alse|FALSE)$/,
		resolve: (str) => new Scalar(str[0] === "t" || str[0] === "T"),
		stringify({ source, value }, ctx) {
			if (source && boolTag.test.test(source)) {
				if (value === (source[0] === "t" || source[0] === "T")) return source;
			}
			return value ? ctx.options.trueStr : ctx.options.falseStr;
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyNumber.js
	function stringifyNumber({ format, minFractionDigits, tag, value }) {
		if (typeof value === "bigint") return String(value);
		const num = typeof value === "number" ? value : Number(value);
		if (!isFinite(num)) return isNaN(num) ? ".nan" : num < 0 ? "-.inf" : ".inf";
		let n = JSON.stringify(value);
		if (!format && minFractionDigits && (!tag || tag === "tag:yaml.org,2002:float") && /^\d/.test(n)) {
			let i = n.indexOf(".");
			if (i < 0) {
				i = n.length;
				n += ".";
			}
			let d = minFractionDigits - (n.length - i - 1);
			while (d-- > 0) n += "0";
		}
		return n;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/core/float.js
	var floatNaN$1 = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
		resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
		stringify: stringifyNumber
	};
	var floatExp$1 = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		format: "EXP",
		test: /^[-+]?(?:\.[0-9]+|[0-9]+(?:\.[0-9]*)?)[eE][-+]?[0-9]+$/,
		resolve: (str) => parseFloat(str),
		stringify(node) {
			const num = Number(node.value);
			return isFinite(num) ? num.toExponential() : stringifyNumber(node);
		}
	};
	var float$1 = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		test: /^[-+]?(?:\.[0-9]+|[0-9]+\.[0-9]*)$/,
		resolve(str) {
			const node = new Scalar(parseFloat(str));
			const dot = str.indexOf(".");
			if (dot !== -1 && str[str.length - 1] === "0") node.minFractionDigits = str.length - dot - 1;
			return node;
		},
		stringify: stringifyNumber
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/core/int.js
	var intIdentify$2 = (value) => typeof value === "bigint" || Number.isInteger(value);
	var intResolve$1 = (str, offset, radix, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str.substring(offset), radix);
	function intStringify$1(node, radix, prefix) {
		const { value } = node;
		if (intIdentify$2(value) && value >= 0) return prefix + value.toString(radix);
		return stringifyNumber(node);
	}
	var intOct$1 = {
		identify: (value) => intIdentify$2(value) && value >= 0,
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "OCT",
		test: /^0o[0-7]+$/,
		resolve: (str, _onError, opt) => intResolve$1(str, 2, 8, opt),
		stringify: (node) => intStringify$1(node, 8, "0o")
	};
	var int$1 = {
		identify: intIdentify$2,
		default: true,
		tag: "tag:yaml.org,2002:int",
		test: /^[-+]?[0-9]+$/,
		resolve: (str, _onError, opt) => intResolve$1(str, 0, 10, opt),
		stringify: stringifyNumber
	};
	var intHex$1 = {
		identify: (value) => intIdentify$2(value) && value >= 0,
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "HEX",
		test: /^0x[0-9a-fA-F]+$/,
		resolve: (str, _onError, opt) => intResolve$1(str, 2, 16, opt),
		stringify: (node) => intStringify$1(node, 16, "0x")
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/core/schema.js
	var schema$2 = [
		map,
		seq,
		string,
		nullTag,
		boolTag,
		intOct$1,
		int$1,
		intHex$1,
		floatNaN$1,
		floatExp$1,
		float$1
	];
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/json/schema.js
	function intIdentify$1(value) {
		return typeof value === "bigint" || Number.isInteger(value);
	}
	var stringifyJSON = ({ value }) => JSON.stringify(value);
	var jsonScalars = [
		{
			identify: (value) => typeof value === "string",
			default: true,
			tag: "tag:yaml.org,2002:str",
			resolve: (str) => str,
			stringify: stringifyJSON
		},
		{
			identify: (value) => value == null,
			createNode: () => new Scalar(null),
			default: true,
			tag: "tag:yaml.org,2002:null",
			test: /^null$/,
			resolve: () => null,
			stringify: stringifyJSON
		},
		{
			identify: (value) => typeof value === "boolean",
			default: true,
			tag: "tag:yaml.org,2002:bool",
			test: /^true$|^false$/,
			resolve: (str) => str === "true",
			stringify: stringifyJSON
		},
		{
			identify: intIdentify$1,
			default: true,
			tag: "tag:yaml.org,2002:int",
			test: /^-?(?:0|[1-9][0-9]*)$/,
			resolve: (str, _onError, { intAsBigInt }) => intAsBigInt ? BigInt(str) : parseInt(str, 10),
			stringify: ({ value }) => intIdentify$1(value) ? value.toString() : JSON.stringify(value)
		},
		{
			identify: (value) => typeof value === "number",
			default: true,
			tag: "tag:yaml.org,2002:float",
			test: /^-?(?:0|[1-9][0-9]*)(?:\.[0-9]*)?(?:[eE][-+]?[0-9]+)?$/,
			resolve: (str) => parseFloat(str),
			stringify: stringifyJSON
		}
	];
	var schema$1 = [map, seq].concat(jsonScalars, {
		default: true,
		tag: "",
		test: /^/,
		resolve(str, onError) {
			onError(`Unresolved plain scalar ${JSON.stringify(str)}`);
			return str;
		}
	});
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/binary.js
	var binary = {
		identify: (value) => value instanceof Uint8Array,
		default: false,
		tag: "tag:yaml.org,2002:binary",
		/**
		* Returns a Buffer in node and an Uint8Array in browsers
		*
		* To use the resulting buffer as an image, you'll want to do something like:
		*
		*   const blob = new Blob([buffer], { type: 'image/jpeg' })
		*   document.querySelector('#photo').src = URL.createObjectURL(blob)
		*/
		resolve(src, onError) {
			if (typeof atob === "function") {
				const str = atob(src.replace(/[\n\r]/g, ""));
				const buffer = new Uint8Array(str.length);
				for (let i = 0; i < str.length; ++i) buffer[i] = str.charCodeAt(i);
				return buffer;
			} else {
				onError("This environment does not support reading binary tags; either Buffer or atob is required");
				return src;
			}
		},
		stringify({ comment, type, value }, ctx, onComment, onChompKeep) {
			if (!value) return "";
			const buf = value;
			let str;
			if (typeof btoa === "function") {
				let s = "";
				for (let i = 0; i < buf.length; ++i) s += String.fromCharCode(buf[i]);
				str = btoa(s);
			} else throw new Error("This environment does not support writing binary tags; either Buffer or btoa is required");
			type ?? (type = Scalar.BLOCK_LITERAL);
			if (type !== Scalar.QUOTE_DOUBLE) {
				const lineWidth = Math.max(ctx.options.lineWidth - ctx.indent.length, ctx.options.minContentWidth);
				const n = Math.ceil(str.length / lineWidth);
				const lines = new Array(n);
				for (let i = 0, o = 0; i < n; ++i, o += lineWidth) lines[i] = str.substr(o, lineWidth);
				str = lines.join(type === Scalar.BLOCK_LITERAL ? "\n" : " ");
			}
			return stringifyString({
				comment,
				type,
				value: str
			}, ctx, onComment, onChompKeep);
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/pairs.js
	function resolvePairs(seq, onError) {
		if (isSeq(seq)) for (let i = 0; i < seq.items.length; ++i) {
			let item = seq.items[i];
			if (isPair(item)) continue;
			else if (isMap(item)) {
				if (item.items.length > 1) onError("Each pair must have its own sequence indicator");
				const pair = item.items[0] || new Pair(new Scalar(null));
				if (item.commentBefore) pair.key.commentBefore = pair.key.commentBefore ? `${item.commentBefore}\n${pair.key.commentBefore}` : item.commentBefore;
				if (item.comment) {
					const cn = pair.value ?? pair.key;
					cn.comment = cn.comment ? `${item.comment}\n${cn.comment}` : item.comment;
				}
				item = pair;
			}
			seq.items[i] = isPair(item) ? item : new Pair(item);
		}
		else onError("Expected a sequence for this tag");
		return seq;
	}
	function createPairs(schema, iterable, ctx) {
		const { replacer } = ctx;
		const pairs = new YAMLSeq(schema);
		pairs.tag = "tag:yaml.org,2002:pairs";
		let i = 0;
		if (iterable && Symbol.iterator in Object(iterable)) for (let it of iterable) {
			if (typeof replacer === "function") it = replacer.call(iterable, String(i++), it);
			let key, value;
			if (Array.isArray(it)) {
				if (it.length === 2) {
					key = it[0];
					value = it[1];
				} else throw new TypeError(`Expected [key, value] tuple: ${it}`);
			} else if (it && it instanceof Object) {
				const keys = Object.keys(it);
				if (keys.length === 1) {
					key = keys[0];
					value = it[key];
				} else throw new TypeError(`Expected tuple with one key, not ${keys.length} keys`);
			} else key = it;
			pairs.items.push(createPair(key, value, ctx));
		}
		return pairs;
	}
	var pairs = {
		collection: "seq",
		default: false,
		tag: "tag:yaml.org,2002:pairs",
		resolve: resolvePairs,
		createNode: createPairs
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/omap.js
	var YAMLOMap = class YAMLOMap extends YAMLSeq {
		constructor() {
			super();
			this.add = YAMLMap.prototype.add.bind(this);
			this.delete = YAMLMap.prototype.delete.bind(this);
			this.get = YAMLMap.prototype.get.bind(this);
			this.has = YAMLMap.prototype.has.bind(this);
			this.set = YAMLMap.prototype.set.bind(this);
			this.tag = YAMLOMap.tag;
		}
		/**
		* If `ctx` is given, the return type is actually `Map<unknown, unknown>`,
		* but TypeScript won't allow widening the signature of a child method.
		*/
		toJSON(_, ctx) {
			if (!ctx) return super.toJSON(_);
			const map = /* @__PURE__ */ new Map();
			if (ctx?.onCreate) ctx.onCreate(map);
			for (const pair of this.items) {
				let key, value;
				if (isPair(pair)) {
					key = toJS(pair.key, "", ctx);
					value = toJS(pair.value, key, ctx);
				} else key = toJS(pair, "", ctx);
				if (map.has(key)) throw new Error("Ordered maps must not include duplicate keys");
				map.set(key, value);
			}
			return map;
		}
		static from(schema, iterable, ctx) {
			const pairs = createPairs(schema, iterable, ctx);
			const omap = new this();
			omap.items = pairs.items;
			return omap;
		}
	};
	YAMLOMap.tag = "tag:yaml.org,2002:omap";
	var omap = {
		collection: "seq",
		identify: (value) => value instanceof Map,
		nodeClass: YAMLOMap,
		default: false,
		tag: "tag:yaml.org,2002:omap",
		resolve(seq, onError) {
			const pairs = resolvePairs(seq, onError);
			const seenKeys = [];
			for (const { key } of pairs.items) if (isScalar(key)) {
				if (seenKeys.includes(key.value)) onError(`Ordered maps must not include duplicate keys: ${key.value}`);
				else seenKeys.push(key.value);
			}
			return Object.assign(new YAMLOMap(), pairs);
		},
		createNode: (schema, iterable, ctx) => YAMLOMap.from(schema, iterable, ctx)
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/bool.js
	function boolStringify({ value, source }, ctx) {
		if (source && (value ? trueTag : falseTag).test.test(source)) return source;
		return value ? ctx.options.trueStr : ctx.options.falseStr;
	}
	var trueTag = {
		identify: (value) => value === true,
		default: true,
		tag: "tag:yaml.org,2002:bool",
		test: /^(?:Y|y|[Yy]es|YES|[Tt]rue|TRUE|[Oo]n|ON)$/,
		resolve: () => new Scalar(true),
		stringify: boolStringify
	};
	var falseTag = {
		identify: (value) => value === false,
		default: true,
		tag: "tag:yaml.org,2002:bool",
		test: /^(?:N|n|[Nn]o|NO|[Ff]alse|FALSE|[Oo]ff|OFF)$/,
		resolve: () => new Scalar(false),
		stringify: boolStringify
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/float.js
	var floatNaN = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		test: /^(?:[-+]?\.(?:inf|Inf|INF)|\.nan|\.NaN|\.NAN)$/,
		resolve: (str) => str.slice(-3).toLowerCase() === "nan" ? NaN : str[0] === "-" ? Number.NEGATIVE_INFINITY : Number.POSITIVE_INFINITY,
		stringify: stringifyNumber
	};
	var floatExp = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		format: "EXP",
		test: /^[-+]?(?:[0-9][0-9_]*)?(?:\.[0-9_]*)?[eE][-+]?[0-9]+$/,
		resolve: (str) => parseFloat(str.replace(/_/g, "")),
		stringify(node) {
			const num = Number(node.value);
			return isFinite(num) ? num.toExponential() : stringifyNumber(node);
		}
	};
	var float = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		test: /^[-+]?(?:[0-9][0-9_]*)?\.[0-9_]*$/,
		resolve(str) {
			const node = new Scalar(parseFloat(str.replace(/_/g, "")));
			const dot = str.indexOf(".");
			if (dot !== -1) {
				const f = str.substring(dot + 1).replace(/_/g, "");
				if (f[f.length - 1] === "0") node.minFractionDigits = f.length;
			}
			return node;
		},
		stringify: stringifyNumber
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/int.js
	var intIdentify = (value) => typeof value === "bigint" || Number.isInteger(value);
	function intResolve(str, offset, radix, { intAsBigInt }) {
		const sign = str[0];
		if (sign === "-" || sign === "+") offset += 1;
		str = str.substring(offset).replace(/_/g, "");
		if (intAsBigInt) {
			switch (radix) {
				case 2:
					str = `0b${str}`;
					break;
				case 8:
					str = `0o${str}`;
					break;
				case 16: str = `0x${str}`;
			}
			const n = BigInt(str);
			return sign === "-" ? BigInt(-1) * n : n;
		}
		const n = parseInt(str, radix);
		return sign === "-" ? -1 * n : n;
	}
	function intStringify(node, radix, prefix) {
		const { value } = node;
		if (intIdentify(value)) {
			const str = value.toString(radix);
			return value < 0 ? "-" + prefix + str.substr(1) : prefix + str;
		}
		return stringifyNumber(node);
	}
	var intBin = {
		identify: intIdentify,
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "BIN",
		test: /^[-+]?0b[0-1_]+$/,
		resolve: (str, _onError, opt) => intResolve(str, 2, 2, opt),
		stringify: (node) => intStringify(node, 2, "0b")
	};
	var intOct = {
		identify: intIdentify,
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "OCT",
		test: /^[-+]?0[0-7_]+$/,
		resolve: (str, _onError, opt) => intResolve(str, 1, 8, opt),
		stringify: (node) => intStringify(node, 8, "0")
	};
	var int = {
		identify: intIdentify,
		default: true,
		tag: "tag:yaml.org,2002:int",
		test: /^[-+]?[0-9][0-9_]*$/,
		resolve: (str, _onError, opt) => intResolve(str, 0, 10, opt),
		stringify: stringifyNumber
	};
	var intHex = {
		identify: intIdentify,
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "HEX",
		test: /^[-+]?0x[0-9a-fA-F_]+$/,
		resolve: (str, _onError, opt) => intResolve(str, 2, 16, opt),
		stringify: (node) => intStringify(node, 16, "0x")
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/set.js
	var YAMLSet = class YAMLSet extends YAMLMap {
		constructor(schema) {
			super(schema);
			this.tag = YAMLSet.tag;
		}
		add(key) {
			let pair;
			if (isPair(key)) pair = key;
			else if (key && typeof key === "object" && "key" in key && "value" in key && key.value === null) pair = new Pair(key.key, null);
			else pair = new Pair(key, null);
			if (!findPair(this.items, pair.key)) this.items.push(pair);
		}
		/**
		* If `keepPair` is `true`, returns the Pair matching `key`.
		* Otherwise, returns the value of that Pair's key.
		*/
		get(key, keepPair) {
			const pair = findPair(this.items, key);
			return !keepPair && isPair(pair) ? isScalar(pair.key) ? pair.key.value : pair.key : pair;
		}
		set(key, value) {
			if (typeof value !== "boolean") throw new Error(`Expected boolean value for set(key, value) in a YAML set, not ${typeof value}`);
			const prev = findPair(this.items, key);
			if (prev && !value) this.items.splice(this.items.indexOf(prev), 1);
			else if (!prev && value) this.items.push(new Pair(key));
		}
		toJSON(_, ctx) {
			return super.toJSON(_, ctx, Set);
		}
		toString(ctx, onComment, onChompKeep) {
			if (!ctx) return JSON.stringify(this);
			if (this.hasAllNullValues(true)) return super.toString(Object.assign({}, ctx, { allNullValues: true }), onComment, onChompKeep);
			else throw new Error("Set items must all have null values");
		}
		static from(schema, iterable, ctx) {
			const { replacer } = ctx;
			const set = new this(schema);
			if (iterable && Symbol.iterator in Object(iterable)) for (let value of iterable) {
				if (typeof replacer === "function") value = replacer.call(iterable, value, value);
				set.items.push(createPair(value, null, ctx));
			}
			return set;
		}
	};
	YAMLSet.tag = "tag:yaml.org,2002:set";
	var set = {
		collection: "map",
		identify: (value) => value instanceof Set,
		nodeClass: YAMLSet,
		default: false,
		tag: "tag:yaml.org,2002:set",
		createNode: (schema, iterable, ctx) => YAMLSet.from(schema, iterable, ctx),
		resolve(map, onError) {
			if (isMap(map)) {
				if (map.hasAllNullValues(true)) return Object.assign(new YAMLSet(), map);
				else onError("Set items must all have null values");
			} else onError("Expected a mapping for this tag");
			return map;
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/timestamp.js
	/** Internal types handle bigint as number, because TS can't figure it out. */
	function parseSexagesimal(str, asBigInt) {
		const sign = str[0];
		const parts = sign === "-" || sign === "+" ? str.substring(1) : str;
		const num = (n) => asBigInt ? BigInt(n) : Number(n);
		const res = parts.replace(/_/g, "").split(":").reduce((res, p) => res * num(60) + num(p), num(0));
		return sign === "-" ? num(-1) * res : res;
	}
	/**
	* hhhh:mm:ss.sss
	*
	* Internal types handle bigint as number, because TS can't figure it out.
	*/
	function stringifySexagesimal(node) {
		let { value } = node;
		let num = (n) => n;
		if (typeof value === "bigint") num = (n) => BigInt(n);
		else if (isNaN(value) || !isFinite(value)) return stringifyNumber(node);
		let sign = "";
		if (value < 0) {
			sign = "-";
			value *= num(-1);
		}
		const _60 = num(60);
		const parts = [value % _60];
		if (value < 60) parts.unshift(0);
		else {
			value = (value - parts[0]) / _60;
			parts.unshift(value % _60);
			if (value >= 60) {
				value = (value - parts[0]) / _60;
				parts.unshift(value);
			}
		}
		return sign + parts.map((n) => String(n).padStart(2, "0")).join(":").replace(/000000\d*$/, "");
	}
	var intTime = {
		identify: (value) => typeof value === "bigint" || Number.isInteger(value),
		default: true,
		tag: "tag:yaml.org,2002:int",
		format: "TIME",
		test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+$/,
		resolve: (str, _onError, { intAsBigInt }) => parseSexagesimal(str, intAsBigInt),
		stringify: stringifySexagesimal
	};
	var floatTime = {
		identify: (value) => typeof value === "number",
		default: true,
		tag: "tag:yaml.org,2002:float",
		format: "TIME",
		test: /^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*$/,
		resolve: (str) => parseSexagesimal(str, false),
		stringify: stringifySexagesimal
	};
	var timestamp = {
		identify: (value) => value instanceof Date,
		default: true,
		tag: "tag:yaml.org,2002:timestamp",
		test: RegExp("^([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:(?:t|T|[ \\t]+)([0-9]{1,2}):([0-9]{1,2}):([0-9]{1,2}(\\.[0-9]+)?)(?:[ \\t]*(Z|[-+][012]?[0-9](?::[0-9]{2})?))?)?$"),
		resolve(str) {
			const match = str.match(timestamp.test);
			if (!match) throw new Error("!!timestamp expects a date, starting with yyyy-mm-dd");
			const [, year, month, day, hour, minute, second] = match.map(Number);
			const millisec = match[7] ? Number((match[7] + "00").substr(1, 3)) : 0;
			let date = Date.UTC(year, month - 1, day, hour || 0, minute || 0, second || 0, millisec);
			const tz = match[8];
			if (tz && tz !== "Z") {
				let d = parseSexagesimal(tz, false);
				if (Math.abs(d) < 30) d *= 60;
				date -= 6e4 * d;
			}
			return new Date(date);
		},
		stringify: ({ value }) => value?.toISOString().replace(/(T00:00:00)?\.000Z$/, "") ?? ""
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/yaml-1.1/schema.js
	var schema = [
		map,
		seq,
		string,
		nullTag,
		trueTag,
		falseTag,
		intBin,
		intOct,
		int,
		intHex,
		floatNaN,
		floatExp,
		float,
		binary,
		merge,
		omap,
		pairs,
		set,
		intTime,
		floatTime,
		timestamp
	];
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/tags.js
	var schemas = /* @__PURE__ */ new Map([
		["core", schema$2],
		["failsafe", [
			map,
			seq,
			string
		]],
		["json", schema$1],
		["yaml11", schema],
		["yaml-1.1", schema]
	]);
	var tagsByName = {
		binary,
		bool: boolTag,
		float: float$1,
		floatExp: floatExp$1,
		floatNaN: floatNaN$1,
		floatTime,
		int: int$1,
		intHex: intHex$1,
		intOct: intOct$1,
		intTime,
		map,
		merge,
		null: nullTag,
		omap,
		pairs,
		seq,
		set,
		timestamp
	};
	var coreKnownTags = {
		"tag:yaml.org,2002:binary": binary,
		"tag:yaml.org,2002:merge": merge,
		"tag:yaml.org,2002:omap": omap,
		"tag:yaml.org,2002:pairs": pairs,
		"tag:yaml.org,2002:set": set,
		"tag:yaml.org,2002:timestamp": timestamp
	};
	function getTags(customTags, schemaName, addMergeTag) {
		const schemaTags = schemas.get(schemaName);
		if (schemaTags && !customTags) return addMergeTag && !schemaTags.includes(merge) ? schemaTags.concat(merge) : schemaTags.slice();
		let tags = schemaTags;
		if (!tags) {
			if (Array.isArray(customTags)) tags = [];
			else {
				const keys = Array.from(schemas.keys()).filter((key) => key !== "yaml11").map((key) => JSON.stringify(key)).join(", ");
				throw new Error(`Unknown schema "${schemaName}"; use one of ${keys} or define customTags array`);
			}
		}
		if (Array.isArray(customTags)) for (const tag of customTags) tags = tags.concat(tag);
		else if (typeof customTags === "function") tags = customTags(tags.slice());
		if (addMergeTag) tags = tags.concat(merge);
		return tags.reduce((tags, tag) => {
			const tagObj = typeof tag === "string" ? tagsByName[tag] : tag;
			if (!tagObj) {
				const tagName = JSON.stringify(tag);
				const keys = Object.keys(tagsByName).map((key) => JSON.stringify(key)).join(", ");
				throw new Error(`Unknown custom tag ${tagName}; use one of ${keys}`);
			}
			if (!tags.includes(tagObj)) tags.push(tagObj);
			return tags;
		}, []);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/schema/Schema.js
	var sortMapEntriesByKey = (a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0;
	var Schema = class Schema {
		constructor({ compat, customTags, merge, resolveKnownTags, schema, sortMapEntries, toStringDefaults }) {
			this.compat = Array.isArray(compat) ? getTags(compat, "compat") : compat ? getTags(null, compat) : null;
			this.name = typeof schema === "string" && schema || "core";
			this.knownTags = resolveKnownTags ? coreKnownTags : {};
			this.tags = getTags(customTags, this.name, merge);
			this.toStringOptions = toStringDefaults ?? null;
			Object.defineProperty(this, MAP, { value: map });
			Object.defineProperty(this, SCALAR$1, { value: string });
			Object.defineProperty(this, SEQ, { value: seq });
			this.sortMapEntries = typeof sortMapEntries === "function" ? sortMapEntries : sortMapEntries === true ? sortMapEntriesByKey : null;
		}
		clone() {
			const copy = Object.create(Schema.prototype, Object.getOwnPropertyDescriptors(this));
			copy.tags = this.tags.slice();
			return copy;
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/stringify/stringifyDocument.js
	function stringifyDocument(doc, options) {
		const lines = [];
		let hasDirectives = options.directives === true;
		if (options.directives !== false && doc.directives) {
			const dir = doc.directives.toString(doc);
			if (dir) {
				lines.push(dir);
				hasDirectives = true;
			} else if (doc.directives.docStart) hasDirectives = true;
		}
		if (hasDirectives) lines.push("---");
		const ctx = createStringifyContext(doc, options);
		const { commentString } = ctx.options;
		if (doc.commentBefore) {
			if (lines.length !== 1) lines.unshift("");
			const cs = commentString(doc.commentBefore);
			lines.unshift(indentComment(cs, ""));
		}
		let chompKeep = false;
		let contentComment = null;
		if (doc.contents) {
			if (isNode(doc.contents)) {
				if (doc.contents.spaceBefore && hasDirectives) lines.push("");
				if (doc.contents.commentBefore) {
					const cs = commentString(doc.contents.commentBefore);
					lines.push(indentComment(cs, ""));
				}
				ctx.forceBlockIndent = !!doc.comment;
				contentComment = doc.contents.comment;
			}
			const onChompKeep = contentComment ? void 0 : () => chompKeep = true;
			let body = stringify(doc.contents, ctx, () => contentComment = null, onChompKeep);
			if (contentComment) body += lineComment(body, "", commentString(contentComment));
			if ((body[0] === "|" || body[0] === ">") && lines[lines.length - 1] === "---") lines[lines.length - 1] = `--- ${body}`;
			else lines.push(body);
		} else lines.push(stringify(doc.contents, ctx));
		if (doc.directives?.docEnd) {
			if (doc.comment) {
				const cs = commentString(doc.comment);
				if (cs.includes("\n")) {
					lines.push("...");
					lines.push(indentComment(cs, ""));
				} else lines.push(`... ${cs}`);
			} else lines.push("...");
		} else {
			let dc = doc.comment;
			if (dc && chompKeep) dc = dc.replace(/^\n+/, "");
			if (dc) {
				if ((!chompKeep || contentComment) && lines[lines.length - 1] !== "") lines.push("");
				lines.push(indentComment(commentString(dc), ""));
			}
		}
		return lines.join("\n") + "\n";
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/doc/Document.js
	var Document = class Document {
		constructor(value, replacer, options) {
			/** A comment before this Document */
			this.commentBefore = null;
			/** A comment immediately after this Document */
			this.comment = null;
			/** Errors encountered during parsing. */
			this.errors = [];
			/** Warnings encountered during parsing. */
			this.warnings = [];
			Object.defineProperty(this, NODE_TYPE, { value: DOC });
			let _replacer = null;
			if (typeof replacer === "function" || Array.isArray(replacer)) _replacer = replacer;
			else if (options === void 0 && replacer) {
				options = replacer;
				replacer = void 0;
			}
			const opt = Object.assign({
				intAsBigInt: false,
				keepSourceTokens: false,
				logLevel: "warn",
				prettyErrors: true,
				strict: true,
				stringKeys: false,
				uniqueKeys: true,
				version: "1.2"
			}, options);
			this.options = opt;
			let { version } = opt;
			if (options?._directives) {
				this.directives = options._directives.atDocument();
				if (this.directives.yaml.explicit) version = this.directives.yaml.version;
			} else this.directives = new Directives({ version });
			this.setSchema(version, options);
			this.contents = value === void 0 ? null : this.createNode(value, _replacer, options);
		}
		/**
		* Create a deep copy of this Document and its contents.
		*
		* Custom Node values that inherit from `Object` still refer to their original instances.
		*/
		clone() {
			const copy = Object.create(Document.prototype, { [NODE_TYPE]: { value: DOC } });
			copy.commentBefore = this.commentBefore;
			copy.comment = this.comment;
			copy.errors = this.errors.slice();
			copy.warnings = this.warnings.slice();
			copy.options = Object.assign({}, this.options);
			if (this.directives) copy.directives = this.directives.clone();
			copy.schema = this.schema.clone();
			copy.contents = isNode(this.contents) ? this.contents.clone(copy.schema) : this.contents;
			if (this.range) copy.range = this.range.slice();
			return copy;
		}
		/** Adds a value to the document. */
		add(value) {
			if (assertCollection(this.contents)) this.contents.add(value);
		}
		/** Adds a value to the document. */
		addIn(path, value) {
			if (assertCollection(this.contents)) this.contents.addIn(path, value);
		}
		/**
		* Create a new `Alias` node, ensuring that the target `node` has the required anchor.
		*
		* If `node` already has an anchor, `name` is ignored.
		* Otherwise, the `node.anchor` value will be set to `name`,
		* or if an anchor with that name is already present in the document,
		* `name` will be used as a prefix for a new unique anchor.
		* If `name` is undefined, the generated anchor will use 'a' as a prefix.
		*/
		createAlias(node, name) {
			if (!node.anchor) {
				const prev = anchorNames(this);
				node.anchor = !name || prev.has(name) ? findNewAnchor(name || "a", prev) : name;
			}
			return new Alias(node.anchor);
		}
		createNode(value, replacer, options) {
			let _replacer = void 0;
			if (typeof replacer === "function") {
				value = replacer.call({ "": value }, "", value);
				_replacer = replacer;
			} else if (Array.isArray(replacer)) {
				const keyToStr = (v) => typeof v === "number" || v instanceof String || v instanceof Number;
				const asStr = replacer.filter(keyToStr).map(String);
				if (asStr.length > 0) replacer = replacer.concat(asStr);
				_replacer = replacer;
			} else if (options === void 0 && replacer) {
				options = replacer;
				replacer = void 0;
			}
			const { aliasDuplicateObjects, anchorPrefix, flow, keepUndefined, onTagObj, tag } = options ?? {};
			const { onAnchor, setAnchors, sourceObjects } = createNodeAnchors(this, anchorPrefix || "a");
			const ctx = {
				aliasDuplicateObjects: aliasDuplicateObjects ?? true,
				keepUndefined: keepUndefined ?? false,
				onAnchor,
				onTagObj,
				replacer: _replacer,
				schema: this.schema,
				sourceObjects
			};
			const node = createNode(value, tag, ctx);
			if (flow && isCollection(node)) node.flow = true;
			setAnchors();
			return node;
		}
		/**
		* Convert a key and a value into a `Pair` using the current schema,
		* recursively wrapping all values as `Scalar` or `Collection` nodes.
		*/
		createPair(key, value, options = {}) {
			return new Pair(this.createNode(key, null, options), this.createNode(value, null, options));
		}
		/**
		* Removes a value from the document.
		* @returns `true` if the item was found and removed.
		*/
		delete(key) {
			return assertCollection(this.contents) ? this.contents.delete(key) : false;
		}
		/**
		* Removes a value from the document.
		* @returns `true` if the item was found and removed.
		*/
		deleteIn(path) {
			if (isEmptyPath(path)) {
				if (this.contents == null) return false;
				this.contents = null;
				return true;
			}
			return assertCollection(this.contents) ? this.contents.deleteIn(path) : false;
		}
		/**
		* Returns item at `key`, or `undefined` if not found. By default unwraps
		* scalar values from their surrounding node; to disable set `keepScalar` to
		* `true` (collections are always returned intact).
		*/
		get(key, keepScalar) {
			return isCollection(this.contents) ? this.contents.get(key, keepScalar) : void 0;
		}
		/**
		* Returns item at `path`, or `undefined` if not found. By default unwraps
		* scalar values from their surrounding node; to disable set `keepScalar` to
		* `true` (collections are always returned intact).
		*/
		getIn(path, keepScalar) {
			if (isEmptyPath(path)) return !keepScalar && isScalar(this.contents) ? this.contents.value : this.contents;
			return isCollection(this.contents) ? this.contents.getIn(path, keepScalar) : void 0;
		}
		/**
		* Checks if the document includes a value with the key `key`.
		*/
		has(key) {
			return isCollection(this.contents) ? this.contents.has(key) : false;
		}
		/**
		* Checks if the document includes a value at `path`.
		*/
		hasIn(path) {
			if (isEmptyPath(path)) return this.contents !== void 0;
			return isCollection(this.contents) ? this.contents.hasIn(path) : false;
		}
		/**
		* Sets a value in this document. For `!!set`, `value` needs to be a
		* boolean to add/remove the item from the set.
		*/
		set(key, value) {
			if (this.contents == null) this.contents = collectionFromPath(this.schema, [key], value);
			else if (assertCollection(this.contents)) this.contents.set(key, value);
		}
		/**
		* Sets a value in this document. For `!!set`, `value` needs to be a
		* boolean to add/remove the item from the set.
		*/
		setIn(path, value) {
			if (isEmptyPath(path)) this.contents = value;
			else if (this.contents == null) this.contents = collectionFromPath(this.schema, Array.from(path), value);
			else if (assertCollection(this.contents)) this.contents.setIn(path, value);
		}
		/**
		* Change the YAML version and schema used by the document.
		* A `null` version disables support for directives, explicit tags, anchors, and aliases.
		* It also requires the `schema` option to be given as a `Schema` instance value.
		*
		* Overrides all previously set schema options.
		*/
		setSchema(version, options = {}) {
			if (typeof version === "number") version = String(version);
			let opt;
			switch (version) {
				case "1.1":
					if (this.directives) this.directives.yaml.version = "1.1";
					else this.directives = new Directives({ version: "1.1" });
					opt = {
						resolveKnownTags: false,
						schema: "yaml-1.1"
					};
					break;
				case "1.2":
				case "next":
					if (this.directives) this.directives.yaml.version = version;
					else this.directives = new Directives({ version });
					opt = {
						resolveKnownTags: true,
						schema: "core"
					};
					break;
				case null:
					if (this.directives) delete this.directives;
					opt = null;
					break;
				default: {
					const sv = JSON.stringify(version);
					throw new Error(`Expected '1.1', '1.2' or null as first argument, but found: ${sv}`);
				}
			}
			if (options.schema instanceof Object) this.schema = options.schema;
			else if (opt) this.schema = new Schema(Object.assign(opt, options));
			else throw new Error(`With a null YAML version, the { schema: Schema } option is required`);
		}
		toJS({ json, jsonArg, mapAsMap, maxAliasCount, onAnchor, reviver } = {}) {
			const ctx = {
				anchors: /* @__PURE__ */ new Map(),
				doc: this,
				keep: !json,
				mapAsMap: mapAsMap === true,
				mapKeyWarned: false,
				maxAliasCount: typeof maxAliasCount === "number" ? maxAliasCount : 100
			};
			const res = toJS(this.contents, jsonArg ?? "", ctx);
			if (typeof onAnchor === "function") for (const { count, res } of ctx.anchors.values()) onAnchor(res, count);
			return typeof reviver === "function" ? applyReviver(reviver, { "": res }, "", res) : res;
		}
		/**
		* A JSON representation of the document `contents`.
		*
		* @param jsonArg Used by `JSON.stringify` to indicate the array index or
		*   property name.
		*/
		toJSON(jsonArg, onAnchor) {
			return this.toJS({
				json: true,
				jsonArg,
				mapAsMap: false,
				onAnchor
			});
		}
		/** A YAML representation of the document. */
		toString(options = {}) {
			if (this.errors.length > 0) throw new Error("Document with errors cannot be stringified");
			if ("indent" in options && (!Number.isInteger(options.indent) || Number(options.indent) <= 0)) {
				const s = JSON.stringify(options.indent);
				throw new Error(`"indent" option must be a positive integer, not ${s}`);
			}
			return stringifyDocument(this, options);
		}
	};
	function assertCollection(contents) {
		if (isCollection(contents)) return true;
		throw new Error("Expected a YAML collection as document contents");
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/errors.js
	var YAMLError = class extends Error {
		constructor(name, pos, code, message) {
			super();
			this.name = name;
			this.code = code;
			this.message = message;
			this.pos = pos;
		}
	};
	var YAMLParseError = class extends YAMLError {
		constructor(pos, code, message) {
			super("YAMLParseError", pos, code, message);
		}
	};
	var YAMLWarning = class extends YAMLError {
		constructor(pos, code, message) {
			super("YAMLWarning", pos, code, message);
		}
	};
	var prettifyError = (src, lc) => (error) => {
		if (error.pos[0] === -1) return;
		error.linePos = error.pos.map((pos) => lc.linePos(pos));
		const { line, col } = error.linePos[0];
		error.message += ` at line ${line}, column ${col}`;
		let ci = col - 1;
		let lineStr = src.substring(lc.lineStarts[line - 1], lc.lineStarts[line]).replace(/[\n\r]+$/, "");
		if (ci >= 60 && lineStr.length > 80) {
			const trimStart = Math.min(ci - 39, lineStr.length - 79);
			lineStr = "…" + lineStr.substring(trimStart);
			ci -= trimStart - 1;
		}
		if (lineStr.length > 80) lineStr = lineStr.substring(0, 79) + "…";
		if (line > 1 && /^ *$/.test(lineStr.substring(0, ci))) {
			let prev = src.substring(lc.lineStarts[line - 2], lc.lineStarts[line - 1]);
			if (prev.length > 80) prev = prev.substring(0, 79) + "…\n";
			lineStr = prev + lineStr;
		}
		if (/[^ ]/.test(lineStr)) {
			let count = 1;
			const end = error.linePos[1];
			if (end && end.line === line && end.col > col) count = Math.max(1, Math.min(end.col - col, 80 - ci));
			const pointer = " ".repeat(ci) + "^".repeat(count);
			error.message += `:\n\n${lineStr}\n${pointer}\n`;
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-props.js
	function resolveProps(tokens, { flow, indicator, next, offset, onError, parentIndent, startOnNewline }) {
		let spaceBefore = false;
		let atNewline = startOnNewline;
		let hasSpace = startOnNewline;
		let comment = "";
		let commentSep = "";
		let hasNewline = false;
		let reqSpace = false;
		let tab = null;
		let anchor = null;
		let tag = null;
		let newlineAfterProp = null;
		let comma = null;
		let found = null;
		let start = null;
		for (const token of tokens) {
			if (reqSpace) {
				if (token.type !== "space" && token.type !== "newline" && token.type !== "comma") onError(token.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
				reqSpace = false;
			}
			if (tab) {
				if (atNewline && token.type !== "comment" && token.type !== "newline") onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
				tab = null;
			}
			switch (token.type) {
				case "space":
					if (!flow && (indicator !== "doc-start" || next?.type !== "flow-collection") && token.source.includes("	")) tab = token;
					hasSpace = true;
					break;
				case "comment": {
					if (!hasSpace) onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
					const cb = token.source.substring(1) || " ";
					if (!comment) comment = cb;
					else comment += commentSep + cb;
					commentSep = "";
					atNewline = false;
					break;
				}
				case "newline":
					if (atNewline) {
						if (comment) comment += token.source;
						else if (!found || indicator !== "seq-item-ind") spaceBefore = true;
					} else commentSep += token.source;
					atNewline = true;
					hasNewline = true;
					if (anchor || tag) newlineAfterProp = token;
					hasSpace = true;
					break;
				case "anchor":
					if (anchor) onError(token, "MULTIPLE_ANCHORS", "A node can have at most one anchor");
					if (token.source.endsWith(":")) onError(token.offset + token.source.length - 1, "BAD_ALIAS", "Anchor ending in : is ambiguous", true);
					anchor = token;
					start ?? (start = token.offset);
					atNewline = false;
					hasSpace = false;
					reqSpace = true;
					break;
				case "tag":
					if (tag) onError(token, "MULTIPLE_TAGS", "A node can have at most one tag");
					tag = token;
					start ?? (start = token.offset);
					atNewline = false;
					hasSpace = false;
					reqSpace = true;
					break;
				case indicator:
					if (anchor || tag) onError(token, "BAD_PROP_ORDER", `Anchors and tags must be after the ${token.source} indicator`);
					if (found) onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.source} in ${flow ?? "collection"}`);
					found = token;
					atNewline = indicator === "seq-item-ind" || indicator === "explicit-key-ind";
					hasSpace = false;
					break;
				case "comma": if (flow) {
					if (comma) onError(token, "UNEXPECTED_TOKEN", `Unexpected , in ${flow}`);
					comma = token;
					atNewline = false;
					hasSpace = false;
					break;
				}
				default:
					onError(token, "UNEXPECTED_TOKEN", `Unexpected ${token.type} token`);
					atNewline = false;
					hasSpace = false;
			}
		}
		const last = tokens[tokens.length - 1];
		const end = last ? last.offset + last.source.length : offset;
		if (reqSpace && next && next.type !== "space" && next.type !== "newline" && next.type !== "comma" && (next.type !== "scalar" || next.source !== "")) onError(next.offset, "MISSING_CHAR", "Tags and anchors must be separated from the next token by white space");
		if (tab && (atNewline && tab.indent <= parentIndent || next?.type === "block-map" || next?.type === "block-seq")) onError(tab, "TAB_AS_INDENT", "Tabs are not allowed as indentation");
		return {
			comma,
			found,
			spaceBefore,
			comment,
			hasNewline,
			anchor,
			tag,
			newlineAfterProp,
			end,
			start: start ?? end
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/util-contains-newline.js
	function containsNewline(key) {
		if (!key) return null;
		switch (key.type) {
			case "alias":
			case "scalar":
			case "double-quoted-scalar":
			case "single-quoted-scalar":
				if (key.source.includes("\n")) return true;
				if (key.end) {
					for (const st of key.end) if (st.type === "newline") return true;
				}
				return false;
			case "flow-collection":
				for (const it of key.items) {
					for (const st of it.start) if (st.type === "newline") return true;
					if (it.sep) {
						for (const st of it.sep) if (st.type === "newline") return true;
					}
					if (containsNewline(it.key) || containsNewline(it.value)) return true;
				}
				return false;
			default: return true;
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/util-flow-indent-check.js
	function flowIndentCheck(indent, fc, onError) {
		if (fc?.type === "flow-collection") {
			const end = fc.end[0];
			if (end.indent === indent && (end.source === "]" || end.source === "}") && containsNewline(fc)) onError(end, "BAD_INDENT", "Flow end indicator should be more indented than parent", true);
		}
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/util-map-includes.js
	function mapIncludes(ctx, items, search) {
		const { uniqueKeys } = ctx.options;
		if (uniqueKeys === false) return false;
		const isEqual = typeof uniqueKeys === "function" ? uniqueKeys : (a, b) => a === b || isScalar(a) && isScalar(b) && a.value === b.value;
		return items.some((pair) => isEqual(pair.key, search));
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-block-map.js
	var startColMsg = "All mapping items must start at the same column";
	function resolveBlockMap({ composeNode, composeEmptyNode }, ctx, bm, onError, tag) {
		const map = new ((tag?.nodeClass) ?? YAMLMap)(ctx.schema);
		if (ctx.atRoot) ctx.atRoot = false;
		let offset = bm.offset;
		let commentEnd = null;
		for (const collItem of bm.items) {
			const { start, key, sep, value } = collItem;
			const keyProps = resolveProps(start, {
				indicator: "explicit-key-ind",
				next: key ?? sep?.[0],
				offset,
				onError,
				parentIndent: bm.indent,
				startOnNewline: true
			});
			const implicitKey = !keyProps.found;
			if (implicitKey) {
				if (key) {
					if (key.type === "block-seq") onError(offset, "BLOCK_AS_IMPLICIT_KEY", "A block sequence may not be used as an implicit map key");
					else if ("indent" in key && key.indent !== bm.indent) onError(offset, "BAD_INDENT", startColMsg);
				}
				if (!keyProps.anchor && !keyProps.tag && !sep) {
					commentEnd = keyProps.end;
					if (keyProps.comment) {
						if (map.comment) map.comment += "\n" + keyProps.comment;
						else map.comment = keyProps.comment;
					}
					continue;
				}
				if (keyProps.newlineAfterProp || containsNewline(key)) onError(key ?? start[start.length - 1], "MULTILINE_IMPLICIT_KEY", "Implicit keys need to be on a single line");
			} else if (keyProps.found?.indent !== bm.indent) onError(offset, "BAD_INDENT", startColMsg);
			ctx.atKey = true;
			const keyStart = keyProps.end;
			const keyNode = key ? composeNode(ctx, key, keyProps, onError) : composeEmptyNode(ctx, keyStart, start, null, keyProps, onError);
			if (ctx.schema.compat) flowIndentCheck(bm.indent, key, onError);
			ctx.atKey = false;
			if (mapIncludes(ctx, map.items, keyNode)) onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
			const valueProps = resolveProps(sep ?? [], {
				indicator: "map-value-ind",
				next: value,
				offset: keyNode.range[2],
				onError,
				parentIndent: bm.indent,
				startOnNewline: !key || key.type === "block-scalar"
			});
			offset = valueProps.end;
			if (valueProps.found) {
				if (implicitKey) {
					if (value?.type === "block-map" && !valueProps.hasNewline) onError(offset, "BLOCK_AS_IMPLICIT_KEY", "Nested mappings are not allowed in compact mappings");
					if (ctx.options.strict && keyProps.start < valueProps.found.offset - 1024) onError(keyNode.range, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit block mapping key");
				}
				const valueNode = value ? composeNode(ctx, value, valueProps, onError) : composeEmptyNode(ctx, offset, sep, null, valueProps, onError);
				if (ctx.schema.compat) flowIndentCheck(bm.indent, value, onError);
				offset = valueNode.range[2];
				const pair = new Pair(keyNode, valueNode);
				if (ctx.options.keepSourceTokens) pair.srcToken = collItem;
				map.items.push(pair);
			} else {
				if (implicitKey) onError(keyNode.range, "MISSING_CHAR", "Implicit map keys need to be followed by map values");
				if (valueProps.comment) {
					if (keyNode.comment) keyNode.comment += "\n" + valueProps.comment;
					else keyNode.comment = valueProps.comment;
				}
				const pair = new Pair(keyNode);
				if (ctx.options.keepSourceTokens) pair.srcToken = collItem;
				map.items.push(pair);
			}
		}
		if (commentEnd && commentEnd < offset) onError(commentEnd, "IMPOSSIBLE", "Map comment with trailing content");
		map.range = [
			bm.offset,
			offset,
			commentEnd ?? offset
		];
		return map;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-block-seq.js
	function resolveBlockSeq({ composeNode, composeEmptyNode }, ctx, bs, onError, tag) {
		const seq = new ((tag?.nodeClass) ?? YAMLSeq)(ctx.schema);
		if (ctx.atRoot) ctx.atRoot = false;
		if (ctx.atKey) ctx.atKey = false;
		let offset = bs.offset;
		let commentEnd = null;
		for (const { start, value } of bs.items) {
			const props = resolveProps(start, {
				indicator: "seq-item-ind",
				next: value,
				offset,
				onError,
				parentIndent: bs.indent,
				startOnNewline: true
			});
			if (!props.found) {
				if (props.anchor || props.tag || value) {
					if (value && value.type === "block-seq") onError(props.end, "BAD_INDENT", "All sequence items must start at the same column");
					else onError(offset, "MISSING_CHAR", "Sequence item without - indicator");
				} else {
					commentEnd = props.end;
					if (props.comment) seq.comment = props.comment;
					continue;
				}
			}
			const node = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, start, null, props, onError);
			if (ctx.schema.compat) flowIndentCheck(bs.indent, value, onError);
			offset = node.range[2];
			seq.items.push(node);
		}
		seq.range = [
			bs.offset,
			offset,
			commentEnd ?? offset
		];
		return seq;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-end.js
	function resolveEnd(end, offset, reqSpace, onError) {
		let comment = "";
		if (end) {
			let hasSpace = false;
			let sep = "";
			for (const token of end) {
				const { source, type } = token;
				switch (type) {
					case "space":
						hasSpace = true;
						break;
					case "comment": {
						if (reqSpace && !hasSpace) onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
						const cb = source.substring(1) || " ";
						if (!comment) comment = cb;
						else comment += sep + cb;
						sep = "";
						break;
					}
					case "newline":
						if (comment) sep += source;
						hasSpace = true;
						break;
					default: onError(token, "UNEXPECTED_TOKEN", `Unexpected ${type} at node end`);
				}
				offset += source.length;
			}
		}
		return {
			comment,
			offset
		};
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-flow-collection.js
	var blockMsg = "Block collections are not allowed within flow collections";
	var isBlock = (token) => token && (token.type === "block-map" || token.type === "block-seq");
	function resolveFlowCollection({ composeNode, composeEmptyNode }, ctx, fc, onError, tag) {
		const isMap = fc.start.source === "{";
		const fcName = isMap ? "flow map" : "flow sequence";
		const coll = new ((tag?.nodeClass) ?? (isMap ? YAMLMap : YAMLSeq))(ctx.schema);
		coll.flow = true;
		const atRoot = ctx.atRoot;
		if (atRoot) ctx.atRoot = false;
		if (ctx.atKey) ctx.atKey = false;
		let offset = fc.offset + fc.start.source.length;
		for (let i = 0; i < fc.items.length; ++i) {
			const collItem = fc.items[i];
			const { start, key, sep, value } = collItem;
			const props = resolveProps(start, {
				flow: fcName,
				indicator: "explicit-key-ind",
				next: key ?? sep?.[0],
				offset,
				onError,
				parentIndent: fc.indent,
				startOnNewline: false
			});
			if (!props.found) {
				if (!props.anchor && !props.tag && !sep && !value) {
					if (i === 0 && props.comma) onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
					else if (i < fc.items.length - 1) onError(props.start, "UNEXPECTED_TOKEN", `Unexpected empty item in ${fcName}`);
					if (props.comment) {
						if (coll.comment) coll.comment += "\n" + props.comment;
						else coll.comment = props.comment;
					}
					offset = props.end;
					continue;
				}
				if (!isMap && ctx.options.strict && containsNewline(key)) onError(key, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
			}
			if (i === 0) {
				if (props.comma) onError(props.comma, "UNEXPECTED_TOKEN", `Unexpected , in ${fcName}`);
			} else {
				if (!props.comma) onError(props.start, "MISSING_CHAR", `Missing , between ${fcName} items`);
				if (props.comment) {
					let prevItemComment = "";
					loop: for (const st of start) switch (st.type) {
						case "comma":
						case "space": break;
						case "comment":
							prevItemComment = st.source.substring(1);
							break loop;
						default: break loop;
					}
					if (prevItemComment) {
						let prev = coll.items[coll.items.length - 1];
						if (isPair(prev)) prev = prev.value ?? prev.key;
						if (prev.comment) prev.comment += "\n" + prevItemComment;
						else prev.comment = prevItemComment;
						props.comment = props.comment.substring(prevItemComment.length + 1);
					}
				}
			}
			if (!isMap && !sep && !props.found) {
				const valueNode = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, sep, null, props, onError);
				coll.items.push(valueNode);
				offset = valueNode.range[2];
				if (isBlock(value)) onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
			} else {
				ctx.atKey = true;
				const keyStart = props.end;
				const keyNode = key ? composeNode(ctx, key, props, onError) : composeEmptyNode(ctx, keyStart, start, null, props, onError);
				if (isBlock(key)) onError(keyNode.range, "BLOCK_IN_FLOW", blockMsg);
				ctx.atKey = false;
				const valueProps = resolveProps(sep ?? [], {
					flow: fcName,
					indicator: "map-value-ind",
					next: value,
					offset: keyNode.range[2],
					onError,
					parentIndent: fc.indent,
					startOnNewline: false
				});
				if (valueProps.found) {
					if (!isMap && !props.found && ctx.options.strict) {
						if (sep) for (const st of sep) {
							if (st === valueProps.found) break;
							if (st.type === "newline") {
								onError(st, "MULTILINE_IMPLICIT_KEY", "Implicit keys of flow sequence pairs need to be on a single line");
								break;
							}
						}
						if (props.start < valueProps.found.offset - 1024) onError(valueProps.found, "KEY_OVER_1024_CHARS", "The : indicator must be at most 1024 chars after the start of an implicit flow sequence key");
					}
				} else if (value) {
					if ("source" in value && value.source && value.source[0] === ":") onError(value, "MISSING_CHAR", `Missing space after : in ${fcName}`);
					else onError(valueProps.start, "MISSING_CHAR", `Missing , or : between ${fcName} items`);
				}
				const valueNode = value ? composeNode(ctx, value, valueProps, onError) : valueProps.found ? composeEmptyNode(ctx, valueProps.end, sep, null, valueProps, onError) : null;
				if (valueNode) {
					if (isBlock(value)) onError(valueNode.range, "BLOCK_IN_FLOW", blockMsg);
				} else if (valueProps.comment) {
					if (keyNode.comment) keyNode.comment += "\n" + valueProps.comment;
					else keyNode.comment = valueProps.comment;
				}
				const pair = new Pair(keyNode, valueNode);
				if (ctx.options.keepSourceTokens) pair.srcToken = collItem;
				if (isMap) {
					const map = coll;
					if (mapIncludes(ctx, map.items, keyNode)) onError(keyStart, "DUPLICATE_KEY", "Map keys must be unique");
					map.items.push(pair);
				} else {
					const map = new YAMLMap(ctx.schema);
					map.flow = true;
					map.items.push(pair);
					const endRange = (valueNode ?? keyNode).range;
					map.range = [
						keyNode.range[0],
						endRange[1],
						endRange[2]
					];
					coll.items.push(map);
				}
				offset = valueNode ? valueNode.range[2] : valueProps.end;
			}
		}
		const expectedEnd = isMap ? "}" : "]";
		const [ce, ...ee] = fc.end;
		let cePos = offset;
		if (ce && ce.source === expectedEnd) cePos = ce.offset + ce.source.length;
		else {
			const name = fcName[0].toUpperCase() + fcName.substring(1);
			const msg = atRoot ? `${name} must end with a ${expectedEnd}` : `${name} in block collection must be sufficiently indented and end with a ${expectedEnd}`;
			onError(offset, atRoot ? "MISSING_CHAR" : "BAD_INDENT", msg);
			if (ce && ce.source.length !== 1) ee.unshift(ce);
		}
		if (ee.length > 0) {
			const end = resolveEnd(ee, cePos, ctx.options.strict, onError);
			if (end.comment) {
				if (coll.comment) coll.comment += "\n" + end.comment;
				else coll.comment = end.comment;
			}
			coll.range = [
				fc.offset,
				cePos,
				end.offset
			];
		} else coll.range = [
			fc.offset,
			cePos,
			cePos
		];
		return coll;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/compose-collection.js
	function resolveCollection(CN, ctx, token, onError, tagName, tag) {
		const coll = token.type === "block-map" ? resolveBlockMap(CN, ctx, token, onError, tag) : token.type === "block-seq" ? resolveBlockSeq(CN, ctx, token, onError, tag) : resolveFlowCollection(CN, ctx, token, onError, tag);
		const Coll = coll.constructor;
		if (tagName === "!" || tagName === Coll.tagName) {
			coll.tag = Coll.tagName;
			return coll;
		}
		if (tagName) coll.tag = tagName;
		return coll;
	}
	function composeCollection(CN, ctx, token, props, onError) {
		const tagToken = props.tag;
		const tagName = !tagToken ? null : ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg));
		if (token.type === "block-seq") {
			const { anchor, newlineAfterProp: nl } = props;
			const lastProp = anchor && tagToken ? anchor.offset > tagToken.offset ? anchor : tagToken : anchor ?? tagToken;
			if (lastProp && (!nl || nl.offset < lastProp.offset)) onError(lastProp, "MISSING_CHAR", "Missing newline after block sequence props");
		}
		const expType = token.type === "block-map" ? "map" : token.type === "block-seq" ? "seq" : token.start.source === "{" ? "map" : "seq";
		if (!tagToken || !tagName || tagName === "!" || tagName === YAMLMap.tagName && expType === "map" || tagName === YAMLSeq.tagName && expType === "seq") return resolveCollection(CN, ctx, token, onError, tagName);
		let tag = ctx.schema.tags.find((t) => t.tag === tagName && t.collection === expType);
		if (!tag) {
			const kt = ctx.schema.knownTags[tagName];
			if (kt && kt.collection === expType) {
				ctx.schema.tags.push(Object.assign({}, kt, { default: false }));
				tag = kt;
			} else {
				if (kt) onError(tagToken, "BAD_COLLECTION_TYPE", `${kt.tag} used for ${expType} collection, but expects ${kt.collection ?? "scalar"}`, true);
				else onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, true);
				return resolveCollection(CN, ctx, token, onError, tagName);
			}
		}
		const coll = resolveCollection(CN, ctx, token, onError, tagName, tag);
		const res = tag.resolve?.(coll, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg), ctx.options) ?? coll;
		const node = isNode(res) ? res : new Scalar(res);
		node.range = coll.range;
		node.tag = tagName;
		if (tag?.format) node.format = tag.format;
		return node;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-block-scalar.js
	function resolveBlockScalar(ctx, scalar, onError) {
		const start = scalar.offset;
		const header = parseBlockScalarHeader(scalar, ctx.options.strict, onError);
		if (!header) return {
			value: "",
			type: null,
			comment: "",
			range: [
				start,
				start,
				start
			]
		};
		const type = header.mode === ">" ? Scalar.BLOCK_FOLDED : Scalar.BLOCK_LITERAL;
		const lines = scalar.source ? splitLines(scalar.source) : [];
		let chompStart = lines.length;
		for (let i = lines.length - 1; i >= 0; --i) {
			const content = lines[i][1];
			if (content === "" || content === "\r") chompStart = i;
			else break;
		}
		if (chompStart === 0) {
			const value = header.chomp === "+" && lines.length > 0 ? "\n".repeat(Math.max(1, lines.length - 1)) : "";
			let end = start + header.length;
			if (scalar.source) end += scalar.source.length;
			return {
				value,
				type,
				comment: header.comment,
				range: [
					start,
					end,
					end
				]
			};
		}
		let trimIndent = scalar.indent + header.indent;
		let offset = scalar.offset + header.length;
		let contentStart = 0;
		for (let i = 0; i < chompStart; ++i) {
			const [indent, content] = lines[i];
			if (content === "" || content === "\r") {
				if (header.indent === 0 && indent.length > trimIndent) trimIndent = indent.length;
			} else {
				if (indent.length < trimIndent) onError(offset + indent.length, "MISSING_CHAR", "Block scalars with more-indented leading empty lines must use an explicit indentation indicator");
				if (header.indent === 0) trimIndent = indent.length;
				contentStart = i;
				if (trimIndent === 0 && !ctx.atRoot) onError(offset, "BAD_INDENT", "Block scalar values in collections must be indented");
				break;
			}
			offset += indent.length + content.length + 1;
		}
		for (let i = lines.length - 1; i >= chompStart; --i) if (lines[i][0].length > trimIndent) chompStart = i + 1;
		let value = "";
		let sep = "";
		let prevMoreIndented = false;
		for (let i = 0; i < contentStart; ++i) value += lines[i][0].slice(trimIndent) + "\n";
		for (let i = contentStart; i < chompStart; ++i) {
			let [indent, content] = lines[i];
			offset += indent.length + content.length + 1;
			const crlf = content[content.length - 1] === "\r";
			if (crlf) content = content.slice(0, -1);
			/* istanbul ignore if already caught in lexer */
			if (content && indent.length < trimIndent) {
				const message = `Block scalar lines must not be less indented than their ${header.indent ? "explicit indentation indicator" : "first line"}`;
				onError(offset - content.length - (crlf ? 2 : 1), "BAD_INDENT", message);
				indent = "";
			}
			if (type === Scalar.BLOCK_LITERAL) {
				value += sep + indent.slice(trimIndent) + content;
				sep = "\n";
			} else if (indent.length > trimIndent || content[0] === "	") {
				if (sep === " ") sep = "\n";
				else if (!prevMoreIndented && sep === "\n") sep = "\n\n";
				value += sep + indent.slice(trimIndent) + content;
				sep = "\n";
				prevMoreIndented = true;
			} else if (content === "") {
				if (sep === "\n") value += "\n";
				else sep = "\n";
			} else {
				value += sep + content;
				sep = " ";
				prevMoreIndented = false;
			}
		}
		switch (header.chomp) {
			case "-": break;
			case "+":
				for (let i = chompStart; i < lines.length; ++i) value += "\n" + lines[i][0].slice(trimIndent);
				if (value[value.length - 1] !== "\n") value += "\n";
				break;
			default: value += "\n";
		}
		const end = start + header.length + scalar.source.length;
		return {
			value,
			type,
			comment: header.comment,
			range: [
				start,
				end,
				end
			]
		};
	}
	function parseBlockScalarHeader({ offset, props }, strict, onError) {
		/* istanbul ignore if should not happen */
		if (props[0].type !== "block-scalar-header") {
			onError(props[0], "IMPOSSIBLE", "Block scalar header not found");
			return null;
		}
		const { source } = props[0];
		const mode = source[0];
		let indent = 0;
		let chomp = "";
		let error = -1;
		for (let i = 1; i < source.length; ++i) {
			const ch = source[i];
			if (!chomp && (ch === "-" || ch === "+")) chomp = ch;
			else {
				const n = Number(ch);
				if (!indent && n) indent = n;
				else if (error === -1) error = offset + i;
			}
		}
		if (error !== -1) onError(error, "UNEXPECTED_TOKEN", `Block scalar header includes extra characters: ${source}`);
		let hasSpace = false;
		let comment = "";
		let length = source.length;
		for (let i = 1; i < props.length; ++i) {
			const token = props[i];
			switch (token.type) {
				case "space": hasSpace = true;
				case "newline":
					length += token.source.length;
					break;
				case "comment":
					if (strict && !hasSpace) onError(token, "MISSING_CHAR", "Comments must be separated from other tokens by white space characters");
					length += token.source.length;
					comment = token.source.substring(1);
					break;
				case "error":
					onError(token, "UNEXPECTED_TOKEN", token.message);
					length += token.source.length;
					break;
				/* istanbul ignore next should not happen */
				default: {
					onError(token, "UNEXPECTED_TOKEN", `Unexpected token in block scalar header: ${token.type}`);
					const ts = token.source;
					if (ts && typeof ts === "string") length += ts.length;
				}
			}
		}
		return {
			mode,
			indent,
			chomp,
			comment,
			length
		};
	}
	/** @returns Array of lines split up as `[indent, content]` */
	function splitLines(source) {
		const split = source.split(/\n( *)/);
		const first = split[0];
		const m = first.match(/^( *)/);
		const lines = [m?.[1] ? [m[1], first.slice(m[1].length)] : ["", first]];
		for (let i = 1; i < split.length; i += 2) lines.push([split[i], split[i + 1]]);
		return lines;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/resolve-flow-scalar.js
	function resolveFlowScalar(scalar, strict, onError) {
		const { offset, type, source, end } = scalar;
		let _type;
		let value;
		const _onError = (rel, code, msg) => onError(offset + rel, code, msg);
		switch (type) {
			case "scalar":
				_type = Scalar.PLAIN;
				value = plainValue(source, _onError);
				break;
			case "single-quoted-scalar":
				_type = Scalar.QUOTE_SINGLE;
				value = singleQuotedValue(source, _onError);
				break;
			case "double-quoted-scalar":
				_type = Scalar.QUOTE_DOUBLE;
				value = doubleQuotedValue(source, _onError);
				break;
			/* istanbul ignore next should not happen */
			default:
				onError(scalar, "UNEXPECTED_TOKEN", `Expected a flow scalar value, but found: ${type}`);
				return {
					value: "",
					type: null,
					comment: "",
					range: [
						offset,
						offset + source.length,
						offset + source.length
					]
				};
		}
		const valueEnd = offset + source.length;
		const re = resolveEnd(end, valueEnd, strict, onError);
		return {
			value,
			type: _type,
			comment: re.comment,
			range: [
				offset,
				valueEnd,
				re.offset
			]
		};
	}
	function plainValue(source, onError) {
		let badChar = "";
		switch (source[0]) {
			/* istanbul ignore next should not happen */
			case "	":
				badChar = "a tab character";
				break;
			case ",":
				badChar = "flow indicator character ,";
				break;
			case "%":
				badChar = "directive indicator character %";
				break;
			case "|":
			case ">":
				badChar = `block scalar indicator ${source[0]}`;
				break;
			case "@":
			case "`": badChar = `reserved character ${source[0]}`;
		}
		if (badChar) onError(0, "BAD_SCALAR_START", `Plain value cannot start with ${badChar}`);
		return foldLines(source);
	}
	function singleQuotedValue(source, onError) {
		if (source[source.length - 1] !== "'" || source.length === 1) onError(source.length, "MISSING_CHAR", "Missing closing 'quote");
		return foldLines(source.slice(1, -1)).replace(/''/g, "'");
	}
	function foldLines(source) {
		/**
		* The negative lookbehind here and in the `re` RegExp is to
		* prevent causing a polynomial search time in certain cases.
		*
		* The try-catch is for Safari, which doesn't support this yet:
		* https://caniuse.com/js-regexp-lookbehind
		*/
		let first, line;
		try {
			first = /* @__PURE__ */ new RegExp("(.*?)(?<![ 	])[ 	]*\r?\n", "sy");
			line = /* @__PURE__ */ new RegExp("[ 	]*(.*?)(?:(?<![ 	])[ 	]*)?\r?\n", "sy");
		} catch {
			first = /(.*?)[ \t]*\r?\n/sy;
			line = /[ \t]*(.*?)[ \t]*\r?\n/sy;
		}
		let match = first.exec(source);
		if (!match) return source;
		let res = match[1];
		let sep = " ";
		let pos = first.lastIndex;
		line.lastIndex = pos;
		while (match = line.exec(source)) {
			if (match[1] === "") {
				if (sep === "\n") res += sep;
				else sep = "\n";
			} else {
				res += sep + match[1];
				sep = " ";
			}
			pos = line.lastIndex;
		}
		const last = /[ \t]*(.*)/sy;
		last.lastIndex = pos;
		match = last.exec(source);
		return res + sep + (match?.[1] ?? "");
	}
	function doubleQuotedValue(source, onError) {
		let res = "";
		for (let i = 1; i < source.length - 1; ++i) {
			const ch = source[i];
			if (ch === "\r" && source[i + 1] === "\n") continue;
			if (ch === "\n") {
				const { fold, offset } = foldNewline(source, i);
				res += fold;
				i = offset;
			} else if (ch === "\\") {
				let next = source[++i];
				const cc = escapeCodes[next];
				if (cc) res += cc;
				else if (next === "\n") {
					next = source[i + 1];
					while (next === " " || next === "	") next = source[++i + 1];
				} else if (next === "\r" && source[i + 1] === "\n") {
					next = source[++i + 1];
					while (next === " " || next === "	") next = source[++i + 1];
				} else if (next === "x" || next === "u" || next === "U") {
					const length = {
						x: 2,
						u: 4,
						U: 8
					}[next];
					res += parseCharCode(source, i + 1, length, onError);
					i += length;
				} else {
					const raw = source.substr(i - 1, 2);
					onError(i - 1, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
					res += raw;
				}
			} else if (ch === " " || ch === "	") {
				const wsStart = i;
				let next = source[i + 1];
				while (next === " " || next === "	") next = source[++i + 1];
				if (next !== "\n" && !(next === "\r" && source[i + 2] === "\n")) res += i > wsStart ? source.slice(wsStart, i + 1) : ch;
			} else res += ch;
		}
		if (source[source.length - 1] !== "\"" || source.length === 1) onError(source.length, "MISSING_CHAR", "Missing closing \"quote");
		return res;
	}
	/**
	* Fold a single newline into a space, multiple newlines to N - 1 newlines.
	* Presumes `source[offset] === '\n'`
	*/
	function foldNewline(source, offset) {
		let fold = "";
		let ch = source[offset + 1];
		while (ch === " " || ch === "	" || ch === "\n" || ch === "\r") {
			if (ch === "\r" && source[offset + 2] !== "\n") break;
			if (ch === "\n") fold += "\n";
			offset += 1;
			ch = source[offset + 1];
		}
		if (!fold) fold = " ";
		return {
			fold,
			offset
		};
	}
	var escapeCodes = {
		"0": "\0",
		a: "\x07",
		b: "\b",
		e: "\x1B",
		f: "\f",
		n: "\n",
		r: "\r",
		t: "	",
		v: "\v",
		N: "",
		_: "\xA0",
		L: "\u2028",
		P: "\u2029",
		" ": " ",
		"\"": "\"",
		"/": "/",
		"\\": "\\",
		"	": "	"
	};
	function parseCharCode(source, offset, length, onError) {
		const cc = source.substr(offset, length);
		const code = cc.length === length && /^[0-9a-fA-F]+$/.test(cc) ? parseInt(cc, 16) : NaN;
		if (isNaN(code)) {
			const raw = source.substr(offset - 2, length + 2);
			onError(offset - 2, "BAD_DQ_ESCAPE", `Invalid escape sequence ${raw}`);
			return raw;
		}
		return String.fromCodePoint(code);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/compose-scalar.js
	function composeScalar(ctx, token, tagToken, onError) {
		const { value, type, comment, range } = token.type === "block-scalar" ? resolveBlockScalar(ctx, token, onError) : resolveFlowScalar(token, ctx.options.strict, onError);
		const tagName = tagToken ? ctx.directives.tagName(tagToken.source, (msg) => onError(tagToken, "TAG_RESOLVE_FAILED", msg)) : null;
		let tag;
		if (ctx.options.stringKeys && ctx.atKey) tag = ctx.schema[SCALAR$1];
		else if (tagName) tag = findScalarTagByName(ctx.schema, value, tagName, tagToken, onError);
		else if (token.type === "scalar") tag = findScalarTagByTest(ctx, value, token, onError);
		else tag = ctx.schema[SCALAR$1];
		let scalar;
		try {
			const res = tag.resolve(value, (msg) => onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg), ctx.options);
			scalar = isScalar(res) ? res : new Scalar(res);
		} catch (error) {
			const msg = error instanceof Error ? error.message : String(error);
			onError(tagToken ?? token, "TAG_RESOLVE_FAILED", msg);
			scalar = new Scalar(value);
		}
		scalar.range = range;
		scalar.source = value;
		if (type) scalar.type = type;
		if (tagName) scalar.tag = tagName;
		if (tag.format) scalar.format = tag.format;
		if (comment) scalar.comment = comment;
		return scalar;
	}
	function findScalarTagByName(schema, value, tagName, tagToken, onError) {
		if (tagName === "!") return schema[SCALAR$1];
		const matchWithTest = [];
		for (const tag of schema.tags) if (!tag.collection && tag.tag === tagName) {
			if (tag.default && tag.test) matchWithTest.push(tag);
			else return tag;
		}
		for (const tag of matchWithTest) if (tag.test?.test(value)) return tag;
		const kt = schema.knownTags[tagName];
		if (kt && !kt.collection) {
			schema.tags.push(Object.assign({}, kt, {
				default: false,
				test: void 0
			}));
			return kt;
		}
		onError(tagToken, "TAG_RESOLVE_FAILED", `Unresolved tag: ${tagName}`, tagName !== "tag:yaml.org,2002:str");
		return schema[SCALAR$1];
	}
	function findScalarTagByTest({ atKey, directives, schema }, value, token, onError) {
		const tag = schema.tags.find((tag) => (tag.default === true || atKey && tag.default === "key") && tag.test?.test(value)) || schema[SCALAR$1];
		if (schema.compat) {
			const compat = schema.compat.find((tag) => tag.default && tag.test?.test(value)) ?? schema[SCALAR$1];
			if (tag.tag !== compat.tag) onError(token, "TAG_RESOLVE_FAILED", `Value may be parsed as either ${directives.tagString(tag.tag)} or ${directives.tagString(compat.tag)}`, true);
		}
		return tag;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/util-empty-scalar-position.js
	function emptyScalarPosition(offset, before, pos) {
		if (before) {
			pos ?? (pos = before.length);
			for (let i = pos - 1; i >= 0; --i) {
				let st = before[i];
				switch (st.type) {
					case "space":
					case "comment":
					case "newline":
						offset -= st.source.length;
						continue;
				}
				st = before[++i];
				while (st?.type === "space") {
					offset += st.source.length;
					st = before[++i];
				}
				break;
			}
		}
		return offset;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/compose-node.js
	var CN = {
		composeNode,
		composeEmptyNode
	};
	function composeNode(ctx, token, props, onError) {
		const atKey = ctx.atKey;
		const { spaceBefore, comment, anchor, tag } = props;
		let node;
		let isSrcToken = true;
		switch (token.type) {
			case "alias":
				node = composeAlias(ctx, token, onError);
				if (anchor || tag) onError(token, "ALIAS_PROPS", "An alias node must not specify any properties");
				break;
			case "scalar":
			case "single-quoted-scalar":
			case "double-quoted-scalar":
			case "block-scalar":
				node = composeScalar(ctx, token, tag, onError);
				if (anchor) node.anchor = anchor.source.substring(1);
				break;
			case "block-map":
			case "block-seq":
			case "flow-collection":
				node = composeCollection(CN, ctx, token, props, onError);
				if (anchor) node.anchor = anchor.source.substring(1);
				break;
			default:
				onError(token, "UNEXPECTED_TOKEN", token.type === "error" ? token.message : `Unsupported token (type: ${token.type})`);
				node = composeEmptyNode(ctx, token.offset, void 0, null, props, onError);
				isSrcToken = false;
		}
		if (anchor && node.anchor === "") onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
		if (atKey && ctx.options.stringKeys && (!isScalar(node) || typeof node.value !== "string" || node.tag && node.tag !== "tag:yaml.org,2002:str")) onError(tag ?? token, "NON_STRING_KEY", "With stringKeys, all keys must be strings");
		if (spaceBefore) node.spaceBefore = true;
		if (comment) {
			if (token.type === "scalar" && token.source === "") node.comment = comment;
			else node.commentBefore = comment;
		}
		if (ctx.options.keepSourceTokens && isSrcToken) node.srcToken = token;
		return node;
	}
	function composeEmptyNode(ctx, offset, before, pos, { spaceBefore, comment, anchor, tag, end }, onError) {
		const node = composeScalar(ctx, {
			type: "scalar",
			offset: emptyScalarPosition(offset, before, pos),
			indent: -1,
			source: ""
		}, tag, onError);
		if (anchor) {
			node.anchor = anchor.source.substring(1);
			if (node.anchor === "") onError(anchor, "BAD_ALIAS", "Anchor cannot be an empty string");
		}
		if (spaceBefore) node.spaceBefore = true;
		if (comment) {
			node.comment = comment;
			node.range[2] = end;
		}
		return node;
	}
	function composeAlias({ options }, { offset, source, end }, onError) {
		const alias = new Alias(source.substring(1));
		if (alias.source === "") onError(offset, "BAD_ALIAS", "Alias cannot be an empty string");
		if (alias.source.endsWith(":")) onError(offset + source.length - 1, "BAD_ALIAS", "Alias ending in : is ambiguous", true);
		const valueEnd = offset + source.length;
		const re = resolveEnd(end, valueEnd, options.strict, onError);
		alias.range = [
			offset,
			valueEnd,
			re.offset
		];
		if (re.comment) alias.comment = re.comment;
		return alias;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/compose-doc.js
	function composeDoc(options, directives, { offset, start, value, end }, onError) {
		const doc = new Document(void 0, Object.assign({ _directives: directives }, options));
		const ctx = {
			atKey: false,
			atRoot: true,
			directives: doc.directives,
			options: doc.options,
			schema: doc.schema
		};
		const props = resolveProps(start, {
			indicator: "doc-start",
			next: value ?? end?.[0],
			offset,
			onError,
			parentIndent: 0,
			startOnNewline: true
		});
		if (props.found) {
			doc.directives.docStart = true;
			if (value && (value.type === "block-map" || value.type === "block-seq") && !props.hasNewline) onError(props.end, "MISSING_CHAR", "Block collection cannot start on same line with directives-end marker");
		}
		doc.contents = value ? composeNode(ctx, value, props, onError) : composeEmptyNode(ctx, props.end, start, null, props, onError);
		const contentEnd = doc.contents.range[2];
		const re = resolveEnd(end, contentEnd, false, onError);
		if (re.comment) doc.comment = re.comment;
		doc.range = [
			offset,
			contentEnd,
			re.offset
		];
		return doc;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/compose/composer.js
	function getErrorPos(src) {
		if (typeof src === "number") return [src, src + 1];
		if (Array.isArray(src)) return src.length === 2 ? src : [src[0], src[1]];
		const { offset, source } = src;
		return [offset, offset + (typeof source === "string" ? source.length : 1)];
	}
	function parsePrelude(prelude) {
		let comment = "";
		let atComment = false;
		let afterEmptyLine = false;
		for (let i = 0; i < prelude.length; ++i) {
			const source = prelude[i];
			switch (source[0]) {
				case "#":
					comment += (comment === "" ? "" : afterEmptyLine ? "\n\n" : "\n") + (source.substring(1) || " ");
					atComment = true;
					afterEmptyLine = false;
					break;
				case "%":
					if (prelude[i + 1]?.[0] !== "#") i += 1;
					atComment = false;
					break;
				default:
					if (!atComment) afterEmptyLine = true;
					atComment = false;
			}
		}
		return {
			comment,
			afterEmptyLine
		};
	}
	/**
	* Compose a stream of CST nodes into a stream of YAML Documents.
	*
	* ```ts
	* import { Composer, Parser } from 'yaml'
	*
	* const src: string = ...
	* const tokens = new Parser().parse(src)
	* const docs = new Composer().compose(tokens)
	* ```
	*/
	var Composer = class {
		constructor(options = {}) {
			this.doc = null;
			this.atDirectives = false;
			this.prelude = [];
			this.errors = [];
			this.warnings = [];
			this.onError = (source, code, message, warning) => {
				const pos = getErrorPos(source);
				if (warning) this.warnings.push(new YAMLWarning(pos, code, message));
				else this.errors.push(new YAMLParseError(pos, code, message));
			};
			this.directives = new Directives({ version: options.version || "1.2" });
			this.options = options;
		}
		decorate(doc, afterDoc) {
			const { comment, afterEmptyLine } = parsePrelude(this.prelude);
			if (comment) {
				const dc = doc.contents;
				if (afterDoc) doc.comment = doc.comment ? `${doc.comment}\n${comment}` : comment;
				else if (afterEmptyLine || doc.directives.docStart || !dc) doc.commentBefore = comment;
				else if (isCollection(dc) && !dc.flow && dc.items.length > 0) {
					let it = dc.items[0];
					if (isPair(it)) it = it.key;
					const cb = it.commentBefore;
					it.commentBefore = cb ? `${comment}\n${cb}` : comment;
				} else {
					const cb = dc.commentBefore;
					dc.commentBefore = cb ? `${comment}\n${cb}` : comment;
				}
			}
			if (afterDoc) {
				Array.prototype.push.apply(doc.errors, this.errors);
				Array.prototype.push.apply(doc.warnings, this.warnings);
			} else {
				doc.errors = this.errors;
				doc.warnings = this.warnings;
			}
			this.prelude = [];
			this.errors = [];
			this.warnings = [];
		}
		/**
		* Current stream status information.
		*
		* Mostly useful at the end of input for an empty stream.
		*/
		streamInfo() {
			return {
				comment: parsePrelude(this.prelude).comment,
				directives: this.directives,
				errors: this.errors,
				warnings: this.warnings
			};
		}
		/**
		* Compose tokens into documents.
		*
		* @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
		* @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
		*/
		*compose(tokens, forceDoc = false, endOffset = -1) {
			for (const token of tokens) yield* this.next(token);
			yield* this.end(forceDoc, endOffset);
		}
		/** Advance the composer by one CST token. */
		*next(token) {
			switch (token.type) {
				case "directive":
					this.directives.add(token.source, (offset, message, warning) => {
						const pos = getErrorPos(token);
						pos[0] += offset;
						this.onError(pos, "BAD_DIRECTIVE", message, warning);
					});
					this.prelude.push(token.source);
					this.atDirectives = true;
					break;
				case "document": {
					const doc = composeDoc(this.options, this.directives, token, this.onError);
					if (this.atDirectives && !doc.directives.docStart) this.onError(token, "MISSING_CHAR", "Missing directives-end/doc-start indicator line");
					this.decorate(doc, false);
					if (this.doc) yield this.doc;
					this.doc = doc;
					this.atDirectives = false;
					break;
				}
				case "byte-order-mark":
				case "space": break;
				case "comment":
				case "newline":
					this.prelude.push(token.source);
					break;
				case "error": {
					const msg = token.source ? `${token.message}: ${JSON.stringify(token.source)}` : token.message;
					const error = new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", msg);
					if (this.atDirectives || !this.doc) this.errors.push(error);
					else this.doc.errors.push(error);
					break;
				}
				case "doc-end": {
					if (!this.doc) {
						this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", "Unexpected doc-end without preceding document"));
						break;
					}
					this.doc.directives.docEnd = true;
					const end = resolveEnd(token.end, token.offset + token.source.length, this.doc.options.strict, this.onError);
					this.decorate(this.doc, true);
					if (end.comment) {
						const dc = this.doc.comment;
						this.doc.comment = dc ? `${dc}\n${end.comment}` : end.comment;
					}
					this.doc.range[2] = end.offset;
					break;
				}
				default: this.errors.push(new YAMLParseError(getErrorPos(token), "UNEXPECTED_TOKEN", `Unsupported token ${token.type}`));
			}
		}
		/**
		* Call at end of input to yield any remaining document.
		*
		* @param forceDoc - If the stream contains no document, still emit a final document including any comments and directives that would be applied to a subsequent document.
		* @param endOffset - Should be set if `forceDoc` is also set, to set the document range end and to indicate errors correctly.
		*/
		*end(forceDoc = false, endOffset = -1) {
			if (this.doc) {
				this.decorate(this.doc, true);
				yield this.doc;
				this.doc = null;
			} else if (forceDoc) {
				const doc = new Document(void 0, Object.assign({ _directives: this.directives }, this.options));
				if (this.atDirectives) this.onError(endOffset, "MISSING_CHAR", "Missing directives-end indicator line");
				doc.range = [
					0,
					endOffset,
					endOffset
				];
				this.decorate(doc, false);
				yield doc;
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/parse/cst-visit.js
	var BREAK = Symbol("break visit");
	var SKIP = Symbol("skip children");
	var REMOVE = Symbol("remove item");
	/**
	* Apply a visitor to a CST document or item.
	*
	* Walks through the tree (depth-first) starting from the root, calling a
	* `visitor` function with two arguments when entering each item:
	*   - `item`: The current item, which included the following members:
	*     - `start: SourceToken[]` – Source tokens before the key or value,
	*       possibly including its anchor or tag.
	*     - `key?: Token | null` – Set for pair values. May then be `null`, if
	*       the key before the `:` separator is empty.
	*     - `sep?: SourceToken[]` – Source tokens between the key and the value,
	*       which should include the `:` map value indicator if `value` is set.
	*     - `value?: Token` – The value of a sequence item, or of a map pair.
	*   - `path`: The steps from the root to the current node, as an array of
	*     `['key' | 'value', number]` tuples.
	*
	* The return value of the visitor may be used to control the traversal:
	*   - `undefined` (default): Do nothing and continue
	*   - `visit.SKIP`: Do not visit the children of this token, continue with
	*      next sibling
	*   - `visit.BREAK`: Terminate traversal completely
	*   - `visit.REMOVE`: Remove the current item, then continue with the next one
	*   - `number`: Set the index of the next step. This is useful especially if
	*     the index of the current token has changed.
	*   - `function`: Define the next visitor for this item. After the original
	*     visitor is called on item entry, next visitors are called after handling
	*     a non-empty `key` and when exiting the item.
	*/
	function visit(cst, visitor) {
		if ("type" in cst && cst.type === "document") cst = {
			start: cst.start,
			value: cst.value
		};
		_visit(Object.freeze([]), cst, visitor);
	}
	/** Terminate visit traversal completely */
	visit.BREAK = BREAK;
	/** Do not visit the children of the current item */
	visit.SKIP = SKIP;
	/** Remove the current item */
	visit.REMOVE = REMOVE;
	/** Find the item at `path` from `cst` as the root */
	visit.itemAtPath = (cst, path) => {
		let item = cst;
		for (const [field, index] of path) {
			const tok = item?.[field];
			if (tok && "items" in tok) item = tok.items[index];
			else return void 0;
		}
		return item;
	};
	/**
	* Get the immediate parent collection of the item at `path` from `cst` as the root.
	*
	* Throws an error if the collection is not found, which should never happen if the item itself exists.
	*/
	visit.parentCollection = (cst, path) => {
		const parent = visit.itemAtPath(cst, path.slice(0, -1));
		const field = path[path.length - 1][0];
		const coll = parent?.[field];
		if (coll && "items" in coll) return coll;
		throw new Error("Parent collection not found");
	};
	function _visit(path, item, visitor) {
		let ctrl = visitor(item, path);
		if (typeof ctrl === "symbol") return ctrl;
		for (const field of ["key", "value"]) {
			const token = item[field];
			if (token && "items" in token) {
				for (let i = 0; i < token.items.length; ++i) {
					const ci = _visit(Object.freeze(path.concat([[field, i]])), token.items[i], visitor);
					if (typeof ci === "number") i = ci - 1;
					else if (ci === BREAK) return BREAK;
					else if (ci === REMOVE) {
						token.items.splice(i, 1);
						i -= 1;
					}
				}
				if (typeof ctrl === "function" && field === "key") ctrl = ctrl(item, path);
			}
		}
		return typeof ctrl === "function" ? ctrl(item, path) : ctrl;
	}
	/** Identify the type of a lexer token. May return `null` for unknown tokens. */
	function tokenType(source) {
		switch (source) {
			case "﻿": return "byte-order-mark";
			case "": return "doc-mode";
			case "": return "flow-error-end";
			case "": return "scalar";
			case "---": return "doc-start";
			case "...": return "doc-end";
			case "":
			case "\n":
			case "\r\n": return "newline";
			case "-": return "seq-item-ind";
			case "?": return "explicit-key-ind";
			case ":": return "map-value-ind";
			case "{": return "flow-map-start";
			case "}": return "flow-map-end";
			case "[": return "flow-seq-start";
			case "]": return "flow-seq-end";
			case ",": return "comma";
		}
		switch (source[0]) {
			case " ":
			case "	": return "space";
			case "#": return "comment";
			case "%": return "directive-line";
			case "*": return "alias";
			case "&": return "anchor";
			case "!": return "tag";
			case "'": return "single-quoted-scalar";
			case "\"": return "double-quoted-scalar";
			case "|":
			case ">": return "block-scalar-header";
		}
		return null;
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/parse/lexer.js
	function isEmpty(ch) {
		switch (ch) {
			case void 0:
			case " ":
			case "\n":
			case "\r":
			case "	": return true;
			default: return false;
		}
	}
	var hexDigits = /* @__PURE__ */ new Set("0123456789ABCDEFabcdef");
	var tagChars = /* @__PURE__ */ new Set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-#;/?:@&=+$_.!~*'()");
	var flowIndicatorChars = /* @__PURE__ */ new Set(",[]{}");
	var invalidAnchorChars = /* @__PURE__ */ new Set(" ,[]{}\n\r	");
	var isNotAnchorChar = (ch) => !ch || invalidAnchorChars.has(ch);
	/**
	* Splits an input string into lexical tokens, i.e. smaller strings that are
	* easily identifiable by `tokens.tokenType()`.
	*
	* Lexing starts always in a "stream" context. Incomplete input may be buffered
	* until a complete token can be emitted.
	*
	* In addition to slices of the original input, the following control characters
	* may also be emitted:
	*
	* - `\x02` (Start of Text): A document starts with the next token
	* - `\x18` (Cancel): Unexpected end of flow-mode (indicates an error)
	* - `\x1f` (Unit Separator): Next token is a scalar value
	* - `\u{FEFF}` (Byte order mark): Emitted separately outside documents
	*/
	var Lexer = class {
		constructor() {
			/**
			* Flag indicating whether the end of the current buffer marks the end of
			* all input
			*/
			this.atEnd = false;
			/**
			* Explicit indent set in block scalar header, as an offset from the current
			* minimum indent, so e.g. set to 1 from a header `|2+`. Set to -1 if not
			* explicitly set.
			*/
			this.blockScalarIndent = -1;
			/**
			* Block scalars that include a + (keep) chomping indicator in their header
			* include trailing empty lines, which are otherwise excluded from the
			* scalar's contents.
			*/
			this.blockScalarKeep = false;
			/** Current input */
			this.buffer = "";
			/**
			* Flag noting whether the map value indicator : can immediately follow this
			* node within a flow context.
			*/
			this.flowKey = false;
			/** Count of surrounding flow collection levels. */
			this.flowLevel = 0;
			/**
			* Minimum level of indentation required for next lines to be parsed as a
			* part of the current scalar value.
			*/
			this.indentNext = 0;
			/** Indentation level of the current line. */
			this.indentValue = 0;
			/** Position of the next \n character. */
			this.lineEndPos = null;
			/** Stores the state of the lexer if reaching the end of incpomplete input */
			this.next = null;
			/** A pointer to `buffer`; the current position of the lexer. */
			this.pos = 0;
		}
		/**
		* Generate YAML tokens from the `source` string. If `incomplete`,
		* a part of the last line may be left as a buffer for the next call.
		*
		* @returns A generator of lexical tokens
		*/
		*lex(source, incomplete = false) {
			if (source) {
				if (typeof source !== "string") throw TypeError("source is not a string");
				this.buffer = this.buffer ? this.buffer + source : source;
				this.lineEndPos = null;
			}
			this.atEnd = !incomplete;
			let next = this.next ?? "stream";
			while (next && (incomplete || this.hasChars(1))) next = yield* this.parseNext(next);
		}
		atLineEnd() {
			let i = this.pos;
			let ch = this.buffer[i];
			while (ch === " " || ch === "	") ch = this.buffer[++i];
			if (!ch || ch === "#" || ch === "\n") return true;
			if (ch === "\r") return this.buffer[i + 1] === "\n";
			return false;
		}
		charAt(n) {
			return this.buffer[this.pos + n];
		}
		continueScalar(offset) {
			let ch = this.buffer[offset];
			if (this.indentNext > 0) {
				let indent = 0;
				while (ch === " ") ch = this.buffer[++indent + offset];
				if (ch === "\r") {
					const next = this.buffer[indent + offset + 1];
					if (next === "\n" || !next && !this.atEnd) return offset + indent + 1;
				}
				return ch === "\n" || indent >= this.indentNext || !ch && !this.atEnd ? offset + indent : -1;
			}
			if (ch === "-" || ch === ".") {
				const dt = this.buffer.substr(offset, 3);
				if ((dt === "---" || dt === "...") && isEmpty(this.buffer[offset + 3])) return -1;
			}
			return offset;
		}
		getLine() {
			let end = this.lineEndPos;
			if (typeof end !== "number" || end !== -1 && end < this.pos) {
				end = this.buffer.indexOf("\n", this.pos);
				this.lineEndPos = end;
			}
			if (end === -1) return this.atEnd ? this.buffer.substring(this.pos) : null;
			if (this.buffer[end - 1] === "\r") end -= 1;
			return this.buffer.substring(this.pos, end);
		}
		hasChars(n) {
			return this.pos + n <= this.buffer.length;
		}
		setNext(state) {
			this.buffer = this.buffer.substring(this.pos);
			this.pos = 0;
			this.lineEndPos = null;
			this.next = state;
			return null;
		}
		peek(n) {
			return this.buffer.substr(this.pos, n);
		}
		*parseNext(next) {
			switch (next) {
				case "stream": return yield* this.parseStream();
				case "line-start": return yield* this.parseLineStart();
				case "block-start": return yield* this.parseBlockStart();
				case "doc": return yield* this.parseDocument();
				case "flow": return yield* this.parseFlowCollection();
				case "quoted-scalar": return yield* this.parseQuotedScalar();
				case "block-scalar": return yield* this.parseBlockScalar();
				case "plain-scalar": return yield* this.parsePlainScalar();
			}
		}
		*parseStream() {
			let line = this.getLine();
			if (line === null) return this.setNext("stream");
			if (line[0] === "﻿") {
				yield* this.pushCount(1);
				line = line.substring(1);
			}
			if (line[0] === "%") {
				let dirEnd = line.length;
				let cs = line.indexOf("#");
				while (cs !== -1) {
					const ch = line[cs - 1];
					if (ch === " " || ch === "	") {
						dirEnd = cs - 1;
						break;
					} else cs = line.indexOf("#", cs + 1);
				}
				while (true) {
					const ch = line[dirEnd - 1];
					if (ch === " " || ch === "	") dirEnd -= 1;
					else break;
				}
				const n = (yield* this.pushCount(dirEnd)) + (yield* this.pushSpaces(true));
				yield* this.pushCount(line.length - n);
				this.pushNewline();
				return "stream";
			}
			if (this.atLineEnd()) {
				const sp = yield* this.pushSpaces(true);
				yield* this.pushCount(line.length - sp);
				yield* this.pushNewline();
				return "stream";
			}
			yield "";
			return yield* this.parseLineStart();
		}
		*parseLineStart() {
			const ch = this.charAt(0);
			if (!ch && !this.atEnd) return this.setNext("line-start");
			if (ch === "-" || ch === ".") {
				if (!this.atEnd && !this.hasChars(4)) return this.setNext("line-start");
				const s = this.peek(3);
				if ((s === "---" || s === "...") && isEmpty(this.charAt(3))) {
					yield* this.pushCount(3);
					this.indentValue = 0;
					this.indentNext = 0;
					return s === "---" ? "doc" : "stream";
				}
			}
			this.indentValue = yield* this.pushSpaces(false);
			if (this.indentNext > this.indentValue && !isEmpty(this.charAt(1))) this.indentNext = this.indentValue;
			return yield* this.parseBlockStart();
		}
		*parseBlockStart() {
			const [ch0, ch1] = this.peek(2);
			if (!ch1 && !this.atEnd) return this.setNext("block-start");
			if ((ch0 === "-" || ch0 === "?" || ch0 === ":") && isEmpty(ch1)) {
				const n = (yield* this.pushCount(1)) + (yield* this.pushSpaces(true));
				this.indentNext = this.indentValue + 1;
				this.indentValue += n;
				return yield* this.parseBlockStart();
			}
			return "doc";
		}
		*parseDocument() {
			yield* this.pushSpaces(true);
			const line = this.getLine();
			if (line === null) return this.setNext("doc");
			let n = yield* this.pushIndicators();
			switch (line[n]) {
				case "#": yield* this.pushCount(line.length - n);
				case void 0:
					yield* this.pushNewline();
					return yield* this.parseLineStart();
				case "{":
				case "[":
					yield* this.pushCount(1);
					this.flowKey = false;
					this.flowLevel = 1;
					return "flow";
				case "}":
				case "]":
					yield* this.pushCount(1);
					return "doc";
				case "*":
					yield* this.pushUntil(isNotAnchorChar);
					return "doc";
				case "\"":
				case "'": return yield* this.parseQuotedScalar();
				case "|":
				case ">":
					n += yield* this.parseBlockScalarHeader();
					n += yield* this.pushSpaces(true);
					yield* this.pushCount(line.length - n);
					yield* this.pushNewline();
					return yield* this.parseBlockScalar();
				default: return yield* this.parsePlainScalar();
			}
		}
		*parseFlowCollection() {
			let nl, sp;
			let indent = -1;
			do {
				nl = yield* this.pushNewline();
				if (nl > 0) {
					sp = yield* this.pushSpaces(false);
					this.indentValue = indent = sp;
				} else sp = 0;
				sp += yield* this.pushSpaces(true);
			} while (nl + sp > 0);
			const line = this.getLine();
			if (line === null) return this.setNext("flow");
			if (indent !== -1 && indent < this.indentNext && line[0] !== "#" || indent === 0 && (line.startsWith("---") || line.startsWith("...")) && isEmpty(line[3])) {
				if (!(indent === this.indentNext - 1 && this.flowLevel === 1 && (line[0] === "]" || line[0] === "}"))) {
					this.flowLevel = 0;
					yield "";
					return yield* this.parseLineStart();
				}
			}
			let n = 0;
			while (line[n] === ",") {
				n += yield* this.pushCount(1);
				n += yield* this.pushSpaces(true);
				this.flowKey = false;
			}
			n += yield* this.pushIndicators();
			switch (line[n]) {
				case void 0: return "flow";
				case "#":
					yield* this.pushCount(line.length - n);
					return "flow";
				case "{":
				case "[":
					yield* this.pushCount(1);
					this.flowKey = false;
					this.flowLevel += 1;
					return "flow";
				case "}":
				case "]":
					yield* this.pushCount(1);
					this.flowKey = true;
					this.flowLevel -= 1;
					return this.flowLevel ? "flow" : "doc";
				case "*":
					yield* this.pushUntil(isNotAnchorChar);
					return "flow";
				case "\"":
				case "'":
					this.flowKey = true;
					return yield* this.parseQuotedScalar();
				case ":": {
					const next = this.charAt(1);
					if (this.flowKey || isEmpty(next) || next === ",") {
						this.flowKey = false;
						yield* this.pushCount(1);
						yield* this.pushSpaces(true);
						return "flow";
					}
				}
				default:
					this.flowKey = false;
					return yield* this.parsePlainScalar();
			}
		}
		*parseQuotedScalar() {
			const quote = this.charAt(0);
			let end = this.buffer.indexOf(quote, this.pos + 1);
			if (quote === "'") while (end !== -1 && this.buffer[end + 1] === "'") end = this.buffer.indexOf("'", end + 2);
			else while (end !== -1) {
				let n = 0;
				while (this.buffer[end - 1 - n] === "\\") n += 1;
				if (n % 2 === 0) break;
				end = this.buffer.indexOf("\"", end + 1);
			}
			const qb = this.buffer.substring(0, end);
			let nl = qb.indexOf("\n", this.pos);
			if (nl !== -1) {
				while (nl !== -1) {
					const cs = this.continueScalar(nl + 1);
					if (cs === -1) break;
					nl = qb.indexOf("\n", cs);
				}
				if (nl !== -1) end = nl - (qb[nl - 1] === "\r" ? 2 : 1);
			}
			if (end === -1) {
				if (!this.atEnd) return this.setNext("quoted-scalar");
				end = this.buffer.length;
			}
			yield* this.pushToIndex(end + 1, false);
			return this.flowLevel ? "flow" : "doc";
		}
		*parseBlockScalarHeader() {
			this.blockScalarIndent = -1;
			this.blockScalarKeep = false;
			let i = this.pos;
			while (true) {
				const ch = this.buffer[++i];
				if (ch === "+") this.blockScalarKeep = true;
				else if (ch > "0" && ch <= "9") this.blockScalarIndent = Number(ch) - 1;
				else if (ch !== "-") break;
			}
			return yield* this.pushUntil((ch) => isEmpty(ch) || ch === "#");
		}
		*parseBlockScalar() {
			let nl = this.pos - 1;
			let indent = 0;
			let ch;
			loop: for (let i = this.pos; ch = this.buffer[i]; ++i) switch (ch) {
				case " ":
					indent += 1;
					break;
				case "\n":
					nl = i;
					indent = 0;
					break;
				case "\r": {
					const next = this.buffer[i + 1];
					if (!next && !this.atEnd) return this.setNext("block-scalar");
					if (next === "\n") break;
				}
				default: break loop;
			}
			if (!ch && !this.atEnd) return this.setNext("block-scalar");
			if (indent >= this.indentNext) {
				if (this.blockScalarIndent === -1) this.indentNext = indent;
				else this.indentNext = this.blockScalarIndent + (this.indentNext === 0 ? 1 : this.indentNext);
				do {
					const cs = this.continueScalar(nl + 1);
					if (cs === -1) break;
					nl = this.buffer.indexOf("\n", cs);
				} while (nl !== -1);
				if (nl === -1) {
					if (!this.atEnd) return this.setNext("block-scalar");
					nl = this.buffer.length;
				}
			}
			let i = nl + 1;
			ch = this.buffer[i];
			while (ch === " ") ch = this.buffer[++i];
			if (ch === "	") {
				while (ch === "	" || ch === " " || ch === "\r" || ch === "\n") ch = this.buffer[++i];
				nl = i - 1;
			} else if (!this.blockScalarKeep) do {
				let i = nl - 1;
				let ch = this.buffer[i];
				if (ch === "\r") ch = this.buffer[--i];
				const lastChar = i;
				while (ch === " ") ch = this.buffer[--i];
				if (ch === "\n" && i >= this.pos && i + 1 + indent > lastChar) nl = i;
				else break;
			} while (true);
			yield "";
			yield* this.pushToIndex(nl + 1, true);
			return yield* this.parseLineStart();
		}
		*parsePlainScalar() {
			const inFlow = this.flowLevel > 0;
			let end = this.pos - 1;
			let i = this.pos - 1;
			let ch;
			while (ch = this.buffer[++i]) if (ch === ":") {
				const next = this.buffer[i + 1];
				if (isEmpty(next) || inFlow && flowIndicatorChars.has(next)) break;
				end = i;
			} else if (isEmpty(ch)) {
				let next = this.buffer[i + 1];
				if (ch === "\r") {
					if (next === "\n") {
						i += 1;
						ch = "\n";
						next = this.buffer[i + 1];
					} else end = i;
				}
				if (next === "#" || inFlow && flowIndicatorChars.has(next)) break;
				if (ch === "\n") {
					const cs = this.continueScalar(i + 1);
					if (cs === -1) break;
					i = Math.max(i, cs - 2);
				}
			} else {
				if (inFlow && flowIndicatorChars.has(ch)) break;
				end = i;
			}
			if (!ch && !this.atEnd) return this.setNext("plain-scalar");
			yield "";
			yield* this.pushToIndex(end + 1, true);
			return inFlow ? "flow" : "doc";
		}
		*pushCount(n) {
			if (n > 0) {
				yield this.buffer.substr(this.pos, n);
				this.pos += n;
				return n;
			}
			return 0;
		}
		*pushToIndex(i, allowEmpty) {
			const s = this.buffer.slice(this.pos, i);
			if (s) {
				yield s;
				this.pos += s.length;
				return s.length;
			} else if (allowEmpty) yield "";
			return 0;
		}
		*pushIndicators() {
			switch (this.charAt(0)) {
				case "!": return (yield* this.pushTag()) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
				case "&": return (yield* this.pushUntil(isNotAnchorChar)) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
				case "-":
				case "?":
				case ":": {
					const inFlow = this.flowLevel > 0;
					const ch1 = this.charAt(1);
					if (isEmpty(ch1) || inFlow && flowIndicatorChars.has(ch1)) {
						if (!inFlow) this.indentNext = this.indentValue + 1;
						else if (this.flowKey) this.flowKey = false;
						return (yield* this.pushCount(1)) + (yield* this.pushSpaces(true)) + (yield* this.pushIndicators());
					}
				}
			}
			return 0;
		}
		*pushTag() {
			if (this.charAt(1) === "<") {
				let i = this.pos + 2;
				let ch = this.buffer[i];
				while (!isEmpty(ch) && ch !== ">") ch = this.buffer[++i];
				return yield* this.pushToIndex(ch === ">" ? i + 1 : i, false);
			} else {
				let i = this.pos + 1;
				let ch = this.buffer[i];
				while (ch) if (tagChars.has(ch)) ch = this.buffer[++i];
				else if (ch === "%" && hexDigits.has(this.buffer[i + 1]) && hexDigits.has(this.buffer[i + 2])) ch = this.buffer[i += 3];
				else break;
				return yield* this.pushToIndex(i, false);
			}
		}
		*pushNewline() {
			const ch = this.buffer[this.pos];
			if (ch === "\n") return yield* this.pushCount(1);
			else if (ch === "\r" && this.charAt(1) === "\n") return yield* this.pushCount(2);
			else return 0;
		}
		*pushSpaces(allowTabs) {
			let i = this.pos - 1;
			let ch;
			do
				ch = this.buffer[++i];
			while (ch === " " || allowTabs && ch === "	");
			const n = i - this.pos;
			if (n > 0) {
				yield this.buffer.substr(this.pos, n);
				this.pos = i;
			}
			return n;
		}
		*pushUntil(test) {
			let i = this.pos;
			let ch = this.buffer[i];
			while (!test(ch)) ch = this.buffer[++i];
			return yield* this.pushToIndex(i, false);
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/parse/line-counter.js
	/**
	* Tracks newlines during parsing in order to provide an efficient API for
	* determining the one-indexed `{ line, col }` position for any offset
	* within the input.
	*/
	var LineCounter = class {
		constructor() {
			this.lineStarts = [];
			/**
			* Should be called in ascending order. Otherwise, call
			* `lineCounter.lineStarts.sort()` before calling `linePos()`.
			*/
			this.addNewLine = (offset) => this.lineStarts.push(offset);
			/**
			* Performs a binary search and returns the 1-indexed { line, col }
			* position of `offset`. If `line === 0`, `addNewLine` has never been
			* called or `offset` is before the first known newline.
			*/
			this.linePos = (offset) => {
				let low = 0;
				let high = this.lineStarts.length;
				while (low < high) {
					const mid = low + high >> 1;
					if (this.lineStarts[mid] < offset) low = mid + 1;
					else high = mid;
				}
				if (this.lineStarts[low] === offset) return {
					line: low + 1,
					col: 1
				};
				if (low === 0) return {
					line: 0,
					col: offset
				};
				const start = this.lineStarts[low - 1];
				return {
					line: low,
					col: offset - start + 1
				};
			};
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/parse/parser.js
	function includesToken(list, type) {
		for (let i = 0; i < list.length; ++i) if (list[i].type === type) return true;
		return false;
	}
	function findNonEmptyIndex(list) {
		for (let i = 0; i < list.length; ++i) switch (list[i].type) {
			case "space":
			case "comment":
			case "newline": break;
			default: return i;
		}
		return -1;
	}
	function isFlowToken(token) {
		switch (token?.type) {
			case "alias":
			case "scalar":
			case "single-quoted-scalar":
			case "double-quoted-scalar":
			case "flow-collection": return true;
			default: return false;
		}
	}
	function getPrevProps(parent) {
		switch (parent.type) {
			case "document": return parent.start;
			case "block-map": {
				const it = parent.items[parent.items.length - 1];
				return it.sep ?? it.start;
			}
			case "block-seq": return parent.items[parent.items.length - 1].start;
			/* istanbul ignore next should not happen */
			default: return [];
		}
	}
	/** Note: May modify input array */
	function getFirstKeyStartProps(prev) {
		if (prev.length === 0) return [];
		let i = prev.length;
		loop: while (--i >= 0) switch (prev[i].type) {
			case "doc-start":
			case "explicit-key-ind":
			case "map-value-ind":
			case "seq-item-ind":
			case "newline": break loop;
		}
		while (prev[++i]?.type === "space");
		return prev.splice(i, prev.length);
	}
	function fixFlowSeqItems(fc) {
		if (fc.start.type === "flow-seq-start") {
			for (const it of fc.items) if (it.sep && !it.value && !includesToken(it.start, "explicit-key-ind") && !includesToken(it.sep, "map-value-ind")) {
				if (it.key) it.value = it.key;
				delete it.key;
				if (isFlowToken(it.value)) {
					if (it.value.end) Array.prototype.push.apply(it.value.end, it.sep);
					else it.value.end = it.sep;
				} else Array.prototype.push.apply(it.start, it.sep);
				delete it.sep;
			}
		}
	}
	/**
	* A YAML concrete syntax tree (CST) parser
	*
	* ```ts
	* const src: string = ...
	* for (const token of new Parser().parse(src)) {
	*   // token: Token
	* }
	* ```
	*
	* To use the parser with a user-provided lexer:
	*
	* ```ts
	* function* parse(source: string, lexer: Lexer) {
	*   const parser = new Parser()
	*   for (const lexeme of lexer.lex(source))
	*     yield* parser.next(lexeme)
	*   yield* parser.end()
	* }
	*
	* const src: string = ...
	* const lexer = new Lexer()
	* for (const token of parse(src, lexer)) {
	*   // token: Token
	* }
	* ```
	*/
	var Parser = class {
		/**
		* @param onNewLine - If defined, called separately with the start position of
		*   each new line (in `parse()`, including the start of input).
		*/
		constructor(onNewLine) {
			/** If true, space and sequence indicators count as indentation */
			this.atNewLine = true;
			/** If true, next token is a scalar value */
			this.atScalar = false;
			/** Current indentation level */
			this.indent = 0;
			/** Current offset since the start of parsing */
			this.offset = 0;
			/** On the same line with a block map key */
			this.onKeyLine = false;
			/** Top indicates the node that's currently being built */
			this.stack = [];
			/** The source of the current token, set in parse() */
			this.source = "";
			/** The type of the current token, set in parse() */
			this.type = "";
			this.lexer = new Lexer();
			this.onNewLine = onNewLine;
		}
		/**
		* Parse `source` as a YAML stream.
		* If `incomplete`, a part of the last line may be left as a buffer for the next call.
		*
		* Errors are not thrown, but yielded as `{ type: 'error', message }` tokens.
		*
		* @returns A generator of tokens representing each directive, document, and other structure.
		*/
		*parse(source, incomplete = false) {
			if (this.onNewLine && this.offset === 0) this.onNewLine(0);
			for (const lexeme of this.lexer.lex(source, incomplete)) yield* this.next(lexeme);
			if (!incomplete) yield* this.end();
		}
		/**
		* Advance the parser by the `source` of one lexical token.
		*/
		*next(source) {
			this.source = source;
			if (this.atScalar) {
				this.atScalar = false;
				yield* this.step();
				this.offset += source.length;
				return;
			}
			const type = tokenType(source);
			if (!type) {
				const message = `Not a YAML token: ${source}`;
				yield* this.pop({
					type: "error",
					offset: this.offset,
					message,
					source
				});
				this.offset += source.length;
			} else if (type === "scalar") {
				this.atNewLine = false;
				this.atScalar = true;
				this.type = "scalar";
			} else {
				this.type = type;
				yield* this.step();
				switch (type) {
					case "newline":
						this.atNewLine = true;
						this.indent = 0;
						if (this.onNewLine) this.onNewLine(this.offset + source.length);
						break;
					case "space":
						if (this.atNewLine && source[0] === " ") this.indent += source.length;
						break;
					case "explicit-key-ind":
					case "map-value-ind":
					case "seq-item-ind":
						if (this.atNewLine) this.indent += source.length;
						break;
					case "doc-mode":
					case "flow-error-end": return;
					default: this.atNewLine = false;
				}
				this.offset += source.length;
			}
		}
		/** Call at end of input to push out any remaining constructions */
		*end() {
			while (this.stack.length > 0) yield* this.pop();
		}
		get sourceToken() {
			return {
				type: this.type,
				offset: this.offset,
				indent: this.indent,
				source: this.source
			};
		}
		*step() {
			const top = this.peek(1);
			if (this.type === "doc-end" && (!top || top.type !== "doc-end")) {
				while (this.stack.length > 0) yield* this.pop();
				this.stack.push({
					type: "doc-end",
					offset: this.offset,
					source: this.source
				});
				return;
			}
			if (!top) return yield* this.stream();
			switch (top.type) {
				case "document": return yield* this.document(top);
				case "alias":
				case "scalar":
				case "single-quoted-scalar":
				case "double-quoted-scalar": return yield* this.scalar(top);
				case "block-scalar": return yield* this.blockScalar(top);
				case "block-map": return yield* this.blockMap(top);
				case "block-seq": return yield* this.blockSequence(top);
				case "flow-collection": return yield* this.flowCollection(top);
				case "doc-end": return yield* this.documentEnd(top);
			}
			/* istanbul ignore next should not happen */
			yield* this.pop();
		}
		peek(n) {
			return this.stack[this.stack.length - n];
		}
		*pop(error) {
			const token = error ?? this.stack.pop();
			/* istanbul ignore if should not happen */
			if (!token) yield {
				type: "error",
				offset: this.offset,
				source: "",
				message: "Tried to pop an empty stack"
			};
			else if (this.stack.length === 0) yield token;
			else {
				const top = this.peek(1);
				if (token.type === "block-scalar") token.indent = "indent" in top ? top.indent : 0;
				else if (token.type === "flow-collection" && top.type === "document") token.indent = 0;
				if (token.type === "flow-collection") fixFlowSeqItems(token);
				switch (top.type) {
					case "document":
						top.value = token;
						break;
					case "block-scalar":
						top.props.push(token);
						break;
					case "block-map": {
						const it = top.items[top.items.length - 1];
						if (it.value) {
							top.items.push({
								start: [],
								key: token,
								sep: []
							});
							this.onKeyLine = true;
							return;
						} else if (it.sep) it.value = token;
						else {
							Object.assign(it, {
								key: token,
								sep: []
							});
							this.onKeyLine = !it.explicitKey;
							return;
						}
						break;
					}
					case "block-seq": {
						const it = top.items[top.items.length - 1];
						if (it.value) top.items.push({
							start: [],
							value: token
						});
						else it.value = token;
						break;
					}
					case "flow-collection": {
						const it = top.items[top.items.length - 1];
						if (!it || it.value) top.items.push({
							start: [],
							key: token,
							sep: []
						});
						else if (it.sep) it.value = token;
						else Object.assign(it, {
							key: token,
							sep: []
						});
						return;
					}
					/* istanbul ignore next should not happen */
					default:
						yield* this.pop();
						yield* this.pop(token);
				}
				if ((top.type === "document" || top.type === "block-map" || top.type === "block-seq") && (token.type === "block-map" || token.type === "block-seq")) {
					const last = token.items[token.items.length - 1];
					if (last && !last.sep && !last.value && last.start.length > 0 && findNonEmptyIndex(last.start) === -1 && (token.indent === 0 || last.start.every((st) => st.type !== "comment" || st.indent < token.indent))) {
						if (top.type === "document") top.end = last.start;
						else top.items.push({ start: last.start });
						token.items.splice(-1, 1);
					}
				}
			}
		}
		*stream() {
			switch (this.type) {
				case "directive-line":
					yield {
						type: "directive",
						offset: this.offset,
						source: this.source
					};
					return;
				case "byte-order-mark":
				case "space":
				case "comment":
				case "newline":
					yield this.sourceToken;
					return;
				case "doc-mode":
				case "doc-start": {
					const doc = {
						type: "document",
						offset: this.offset,
						start: []
					};
					if (this.type === "doc-start") doc.start.push(this.sourceToken);
					this.stack.push(doc);
					return;
				}
			}
			yield {
				type: "error",
				offset: this.offset,
				message: `Unexpected ${this.type} token in YAML stream`,
				source: this.source
			};
		}
		*document(doc) {
			if (doc.value) return yield* this.lineEnd(doc);
			switch (this.type) {
				case "doc-start":
					if (findNonEmptyIndex(doc.start) !== -1) {
						yield* this.pop();
						yield* this.step();
					} else doc.start.push(this.sourceToken);
					return;
				case "anchor":
				case "tag":
				case "space":
				case "comment":
				case "newline":
					doc.start.push(this.sourceToken);
					return;
			}
			const bv = this.startBlockValue(doc);
			if (bv) this.stack.push(bv);
			else yield {
				type: "error",
				offset: this.offset,
				message: `Unexpected ${this.type} token in YAML document`,
				source: this.source
			};
		}
		*scalar(scalar) {
			if (this.type === "map-value-ind") {
				const start = getFirstKeyStartProps(getPrevProps(this.peek(2)));
				let sep;
				if (scalar.end) {
					sep = scalar.end;
					sep.push(this.sourceToken);
					delete scalar.end;
				} else sep = [this.sourceToken];
				const map = {
					type: "block-map",
					offset: scalar.offset,
					indent: scalar.indent,
					items: [{
						start,
						key: scalar,
						sep
					}]
				};
				this.onKeyLine = true;
				this.stack[this.stack.length - 1] = map;
			} else yield* this.lineEnd(scalar);
		}
		*blockScalar(scalar) {
			switch (this.type) {
				case "space":
				case "comment":
				case "newline":
					scalar.props.push(this.sourceToken);
					return;
				case "scalar":
					scalar.source = this.source;
					this.atNewLine = true;
					this.indent = 0;
					if (this.onNewLine) {
						let nl = this.source.indexOf("\n") + 1;
						while (nl !== 0) {
							this.onNewLine(this.offset + nl);
							nl = this.source.indexOf("\n", nl) + 1;
						}
					}
					yield* this.pop();
					break;
				/* istanbul ignore next should not happen */
				default:
					yield* this.pop();
					yield* this.step();
			}
		}
		*blockMap(map) {
			const it = map.items[map.items.length - 1];
			switch (this.type) {
				case "newline":
					this.onKeyLine = false;
					if (it.value) {
						const end = "end" in it.value ? it.value.end : void 0;
						if ((Array.isArray(end) ? end[end.length - 1] : void 0)?.type === "comment") end?.push(this.sourceToken);
						else map.items.push({ start: [this.sourceToken] });
					} else if (it.sep) it.sep.push(this.sourceToken);
					else it.start.push(this.sourceToken);
					return;
				case "space":
				case "comment":
					if (it.value) map.items.push({ start: [this.sourceToken] });
					else if (it.sep) it.sep.push(this.sourceToken);
					else {
						if (this.atIndentedComment(it.start, map.indent)) {
							const end = map.items[map.items.length - 2]?.value?.end;
							if (Array.isArray(end)) {
								Array.prototype.push.apply(end, it.start);
								end.push(this.sourceToken);
								map.items.pop();
								return;
							}
						}
						it.start.push(this.sourceToken);
					}
					return;
			}
			if (this.indent >= map.indent) {
				const atMapIndent = !this.onKeyLine && this.indent === map.indent;
				const atNextItem = atMapIndent && (it.sep || it.explicitKey) && this.type !== "seq-item-ind";
				let start = [];
				if (atNextItem && it.sep && !it.value) {
					const nl = [];
					for (let i = 0; i < it.sep.length; ++i) {
						const st = it.sep[i];
						switch (st.type) {
							case "newline":
								nl.push(i);
								break;
							case "space": break;
							case "comment":
								if (st.indent > map.indent) nl.length = 0;
								break;
							default: nl.length = 0;
						}
					}
					if (nl.length >= 2) start = it.sep.splice(nl[1]);
				}
				switch (this.type) {
					case "anchor":
					case "tag":
						if (atNextItem || it.value) {
							start.push(this.sourceToken);
							map.items.push({ start });
							this.onKeyLine = true;
						} else if (it.sep) it.sep.push(this.sourceToken);
						else it.start.push(this.sourceToken);
						return;
					case "explicit-key-ind":
						if (!it.sep && !it.explicitKey) {
							it.start.push(this.sourceToken);
							it.explicitKey = true;
						} else if (atNextItem || it.value) {
							start.push(this.sourceToken);
							map.items.push({
								start,
								explicitKey: true
							});
						} else this.stack.push({
							type: "block-map",
							offset: this.offset,
							indent: this.indent,
							items: [{
								start: [this.sourceToken],
								explicitKey: true
							}]
						});
						this.onKeyLine = true;
						return;
					case "map-value-ind":
						if (it.explicitKey) {
							if (!it.sep) {
								if (includesToken(it.start, "newline")) Object.assign(it, {
									key: null,
									sep: [this.sourceToken]
								});
								else {
									const start = getFirstKeyStartProps(it.start);
									this.stack.push({
										type: "block-map",
										offset: this.offset,
										indent: this.indent,
										items: [{
											start,
											key: null,
											sep: [this.sourceToken]
										}]
									});
								}
							} else if (it.value) map.items.push({
								start: [],
								key: null,
								sep: [this.sourceToken]
							});
							else if (includesToken(it.sep, "map-value-ind")) this.stack.push({
								type: "block-map",
								offset: this.offset,
								indent: this.indent,
								items: [{
									start,
									key: null,
									sep: [this.sourceToken]
								}]
							});
							else if (isFlowToken(it.key) && !includesToken(it.sep, "newline")) {
								const start = getFirstKeyStartProps(it.start);
								const key = it.key;
								const sep = it.sep;
								sep.push(this.sourceToken);
								delete it.key;
								delete it.sep;
								this.stack.push({
									type: "block-map",
									offset: this.offset,
									indent: this.indent,
									items: [{
										start,
										key,
										sep
									}]
								});
							} else if (start.length > 0) it.sep = it.sep.concat(start, this.sourceToken);
							else it.sep.push(this.sourceToken);
						} else if (!it.sep) Object.assign(it, {
							key: null,
							sep: [this.sourceToken]
						});
						else if (it.value || atNextItem) map.items.push({
							start,
							key: null,
							sep: [this.sourceToken]
						});
						else if (includesToken(it.sep, "map-value-ind")) this.stack.push({
							type: "block-map",
							offset: this.offset,
							indent: this.indent,
							items: [{
								start: [],
								key: null,
								sep: [this.sourceToken]
							}]
						});
						else it.sep.push(this.sourceToken);
						this.onKeyLine = true;
						return;
					case "alias":
					case "scalar":
					case "single-quoted-scalar":
					case "double-quoted-scalar": {
						const fs = this.flowScalar(this.type);
						if (atNextItem || it.value) {
							map.items.push({
								start,
								key: fs,
								sep: []
							});
							this.onKeyLine = true;
						} else if (it.sep) this.stack.push(fs);
						else {
							Object.assign(it, {
								key: fs,
								sep: []
							});
							this.onKeyLine = true;
						}
						return;
					}
					default: {
						const bv = this.startBlockValue(map);
						if (bv) {
							if (bv.type === "block-seq") {
								if (!it.explicitKey && it.sep && !includesToken(it.sep, "newline")) {
									yield* this.pop({
										type: "error",
										offset: this.offset,
										message: "Unexpected block-seq-ind on same line with key",
										source: this.source
									});
									return;
								}
							} else if (atMapIndent) map.items.push({ start });
							this.stack.push(bv);
							return;
						}
					}
				}
			}
			yield* this.pop();
			yield* this.step();
		}
		*blockSequence(seq) {
			const it = seq.items[seq.items.length - 1];
			switch (this.type) {
				case "newline":
					if (it.value) {
						const end = "end" in it.value ? it.value.end : void 0;
						if ((Array.isArray(end) ? end[end.length - 1] : void 0)?.type === "comment") end?.push(this.sourceToken);
						else seq.items.push({ start: [this.sourceToken] });
					} else it.start.push(this.sourceToken);
					return;
				case "space":
				case "comment":
					if (it.value) seq.items.push({ start: [this.sourceToken] });
					else {
						if (this.atIndentedComment(it.start, seq.indent)) {
							const end = seq.items[seq.items.length - 2]?.value?.end;
							if (Array.isArray(end)) {
								Array.prototype.push.apply(end, it.start);
								end.push(this.sourceToken);
								seq.items.pop();
								return;
							}
						}
						it.start.push(this.sourceToken);
					}
					return;
				case "anchor":
				case "tag":
					if (it.value || this.indent <= seq.indent) break;
					it.start.push(this.sourceToken);
					return;
				case "seq-item-ind":
					if (this.indent !== seq.indent) break;
					if (it.value || includesToken(it.start, "seq-item-ind")) seq.items.push({ start: [this.sourceToken] });
					else it.start.push(this.sourceToken);
					return;
			}
			if (this.indent > seq.indent) {
				const bv = this.startBlockValue(seq);
				if (bv) {
					this.stack.push(bv);
					return;
				}
			}
			yield* this.pop();
			yield* this.step();
		}
		*flowCollection(fc) {
			const it = fc.items[fc.items.length - 1];
			if (this.type === "flow-error-end") {
				let top;
				do {
					yield* this.pop();
					top = this.peek(1);
				} while (top && top.type === "flow-collection");
			} else if (fc.end.length === 0) {
				switch (this.type) {
					case "comma":
					case "explicit-key-ind":
						if (!it || it.sep) fc.items.push({ start: [this.sourceToken] });
						else it.start.push(this.sourceToken);
						return;
					case "map-value-ind":
						if (!it || it.value) fc.items.push({
							start: [],
							key: null,
							sep: [this.sourceToken]
						});
						else if (it.sep) it.sep.push(this.sourceToken);
						else Object.assign(it, {
							key: null,
							sep: [this.sourceToken]
						});
						return;
					case "space":
					case "comment":
					case "newline":
					case "anchor":
					case "tag":
						if (!it || it.value) fc.items.push({ start: [this.sourceToken] });
						else if (it.sep) it.sep.push(this.sourceToken);
						else it.start.push(this.sourceToken);
						return;
					case "alias":
					case "scalar":
					case "single-quoted-scalar":
					case "double-quoted-scalar": {
						const fs = this.flowScalar(this.type);
						if (!it || it.value) fc.items.push({
							start: [],
							key: fs,
							sep: []
						});
						else if (it.sep) this.stack.push(fs);
						else Object.assign(it, {
							key: fs,
							sep: []
						});
						return;
					}
					case "flow-map-end":
					case "flow-seq-end":
						fc.end.push(this.sourceToken);
						return;
				}
				const bv = this.startBlockValue(fc);
				/* istanbul ignore else should not happen */
				if (bv) this.stack.push(bv);
				else {
					yield* this.pop();
					yield* this.step();
				}
			} else {
				const parent = this.peek(2);
				if (parent.type === "block-map" && (this.type === "map-value-ind" && parent.indent === fc.indent || this.type === "newline" && !parent.items[parent.items.length - 1].sep)) {
					yield* this.pop();
					yield* this.step();
				} else if (this.type === "map-value-ind" && parent.type !== "flow-collection") {
					const start = getFirstKeyStartProps(getPrevProps(parent));
					fixFlowSeqItems(fc);
					const sep = fc.end.splice(1, fc.end.length);
					sep.push(this.sourceToken);
					const map = {
						type: "block-map",
						offset: fc.offset,
						indent: fc.indent,
						items: [{
							start,
							key: fc,
							sep
						}]
					};
					this.onKeyLine = true;
					this.stack[this.stack.length - 1] = map;
				} else yield* this.lineEnd(fc);
			}
		}
		flowScalar(type) {
			if (this.onNewLine) {
				let nl = this.source.indexOf("\n") + 1;
				while (nl !== 0) {
					this.onNewLine(this.offset + nl);
					nl = this.source.indexOf("\n", nl) + 1;
				}
			}
			return {
				type,
				offset: this.offset,
				indent: this.indent,
				source: this.source
			};
		}
		startBlockValue(parent) {
			switch (this.type) {
				case "alias":
				case "scalar":
				case "single-quoted-scalar":
				case "double-quoted-scalar": return this.flowScalar(this.type);
				case "block-scalar-header": return {
					type: "block-scalar",
					offset: this.offset,
					indent: this.indent,
					props: [this.sourceToken],
					source: ""
				};
				case "flow-map-start":
				case "flow-seq-start": return {
					type: "flow-collection",
					offset: this.offset,
					indent: this.indent,
					start: this.sourceToken,
					items: [],
					end: []
				};
				case "seq-item-ind": return {
					type: "block-seq",
					offset: this.offset,
					indent: this.indent,
					items: [{ start: [this.sourceToken] }]
				};
				case "explicit-key-ind": {
					this.onKeyLine = true;
					const start = getFirstKeyStartProps(getPrevProps(parent));
					start.push(this.sourceToken);
					return {
						type: "block-map",
						offset: this.offset,
						indent: this.indent,
						items: [{
							start,
							explicitKey: true
						}]
					};
				}
				case "map-value-ind": {
					this.onKeyLine = true;
					const start = getFirstKeyStartProps(getPrevProps(parent));
					return {
						type: "block-map",
						offset: this.offset,
						indent: this.indent,
						items: [{
							start,
							key: null,
							sep: [this.sourceToken]
						}]
					};
				}
			}
			return null;
		}
		atIndentedComment(start, indent) {
			if (this.type !== "comment") return false;
			if (this.indent <= indent) return false;
			return start.every((st) => st.type === "newline" || st.type === "space");
		}
		*documentEnd(docEnd) {
			if (this.type !== "doc-mode") {
				if (docEnd.end) docEnd.end.push(this.sourceToken);
				else docEnd.end = [this.sourceToken];
				if (this.type === "newline") yield* this.pop();
			}
		}
		*lineEnd(token) {
			switch (this.type) {
				case "comma":
				case "doc-start":
				case "doc-end":
				case "flow-seq-end":
				case "flow-map-end":
				case "map-value-ind":
					yield* this.pop();
					yield* this.step();
					break;
				case "newline": this.onKeyLine = false;
				default:
					if (token.end) token.end.push(this.sourceToken);
					else token.end = [this.sourceToken];
					if (this.type === "newline") yield* this.pop();
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/client/node_modules/.pnpm/yaml@2.8.1/node_modules/yaml/browser/dist/public-api.js
	function parseOptions(options) {
		const prettyErrors = options.prettyErrors !== false;
		return {
			lineCounter: options.lineCounter || prettyErrors && new LineCounter() || null,
			prettyErrors
		};
	}
	/** Parse an input string into a single YAML.Document */
	function parseDocument(source, options = {}) {
		const { lineCounter, prettyErrors } = parseOptions(options);
		const parser = new Parser(lineCounter?.addNewLine);
		const composer = new Composer(options);
		let doc = null;
		for (const _doc of composer.compose(parser.parse(source), true, source.length)) if (!doc) doc = _doc;
		else if (doc.options.logLevel !== "silent") {
			doc.errors.push(new YAMLParseError(_doc.range.slice(0, 2), "MULTIPLE_DOCS", "Source contains multiple documents; please use YAML.parseAllDocuments()"));
			break;
		}
		if (prettyErrors && lineCounter) {
			doc.errors.forEach(prettifyError(source, lineCounter));
			doc.warnings.forEach(prettifyError(source, lineCounter));
		}
		return doc;
	}
	function parse(src, reviver, options) {
		let _reviver = void 0;
		if (typeof reviver === "function") _reviver = reviver;
		else if (options === void 0 && reviver && typeof reviver === "object") options = reviver;
		const doc = parseDocument(src, options);
		if (!doc) return null;
		doc.warnings.forEach((warning) => warn(doc.options.logLevel, warning));
		if (doc.errors.length > 0) {
			if (doc.options.logLevel !== "silent") throw doc.errors[0];
			else doc.errors = [];
		}
		return doc.toJS(Object.assign({ reviver: _reviver }, options));
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/content/ui/region_themes.yaml?raw
	var region_themes_default = "# 區域主題點綴（Phase RT-1；docs/art/區域主題移植需求.md 第 1 節、樣張 docs/art/region-themes.png）。純顯示資料，不進引擎結算。\n# 全域層（版面、字型、按鈕、深藍底、金色主框）每區都一樣；這裡只決定會依區域換的點綴：\n#   accent：強調色（滑過、選取的細光、標題牌內框細線）；corner：主框四角的飾件（畫法在 client/src/ui/regionCorners.ts）；\n#   plaque：地名標題牌的材質（下方 plaques 的兩色漸層）；portrait_ring：主角、NPC、說書人的頭像框色；\n#   ink、seal：等待動畫（RT-3）的墨色與封蠟色；wait_fx：等待動畫的點綴（RT-3 讀；none＝沒有、ember＝飄起的火星、crystal＝紫晶光）。\n# 沒有區域時（標題、建角、讀檔）與讀不到區域時一律用 hub。前端在 build 時匯入這份檔（client/src/ui/regionTheme.ts），\n# Python 的 trpg.content.ui_themes（`trpg content check`）驗證同一份檔。新增一區：加一列即可，不用改程式。\nplaques:\n  crystal: {top: \"#2a2a5a\", bottom: \"#1a1a3a\"}\n  jade:    {top: \"#2f4a3a\", bottom: \"#1f3428\"}\n  iron:    {top: \"#4a4044\", bottom: \"#2a2426\"}\n  marble:  {top: \"#3e4466\", bottom: \"#24283e\"}\n  brass:   {top: \"#4e4228\", bottom: \"#2c2416\"}\n  sea:     {top: \"#1f4656\", bottom: \"#132c38\"}\nthemes:\n  hub:           {accent: \"#a898ff\", corner: filigree, plaque: crystal, portrait_ring: \"#a898ff\", ink: \"#22305a\", seal: \"#7a5ad0\", wait_fx: crystal}\n  capital:       {accent: \"#a898ff\", corner: filigree, plaque: crystal, portrait_ring: \"#a898ff\", ink: \"#22305a\", seal: \"#7a5ad0\", wait_fx: crystal}\n  cloud_ridge:   {accent: \"#6aa84a\", corner: cloud,    plaque: jade,    portrait_ring: \"#6aa84a\", ink: \"#1c1712\", seal: \"#b8432f\"}\n  ashen_waste:   {accent: \"#ff6a1a\", corner: rivet,    plaque: iron,    portrait_ring: \"#ff6a1a\", ink: \"#3a1a10\", seal: \"#ff6a1a\", wait_fx: ember}\n  crystal_crown: {accent: \"#8ab0ff\", corner: shard,    plaque: marble,  portrait_ring: \"#8ab0ff\", ink: \"#2a2a5a\", seal: \"#5a7ad0\"}\n  arcane_hub:    {accent: \"#4ad0c8\", corner: gear,     plaque: brass,   portrait_ring: \"#4ad0c8\", ink: \"#2a2418\", seal: \"#c87a2a\"}\n  frost_tide:    {accent: \"#6ac0e8\", corner: shell,    plaque: sea,     portrait_ring: \"#6ac0e8\", ink: \"#1a3a4a\", seal: \"#e88a7a\"}\n";
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/ui/regionCorners.ts
	var CORNER_KINDS = [
		"filigree",
		"cloud",
		"rivet",
		"shard",
		"gear",
		"shell"
	];
	var GOLD2 = "#e8bb48";
	/** 一種飾件的 SVG 內容（左上角方向、18×18 座標）。 */
	function cornerShapes(kind, c) {
		switch (kind) {
			case "cloud": return `<path d="M4 10A6 6 0 0 1 15.4 7.4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/><path d="M12 5A3 3 0 0 1 17.5 4" fill="none" stroke="${c.accent}" stroke-width="1.6" stroke-linecap="round"/><path d="M6 14A3 3 0 0 1 6 8" fill="none" stroke="${c.accent}" stroke-width="1.2" stroke-linecap="round"/><circle cx="4" cy="4" r="2.5" fill="${c.seal}"/>`;
			case "rivet": return `<path d="M0 0H18V6H6V18H0Z" fill="#5a5a60"/><path d="M0 0H18V1H1V18H0Z" fill="#7a7a80"/><circle cx="3" cy="3" r="1.6" fill="#9a9aa0"/><circle cx="12" cy="3" r="1.6" fill="#9a9aa0"/><circle cx="3" cy="12" r="1.6" fill="#9a9aa0"/><rect x="15" y="2" width="3" height="2" fill="${c.accent}" opacity="0.75"/>`;
			case "shard": return `<path d="M1 1L11 3L4 10Z" fill="${c.accent}" stroke="#eef2ff" stroke-width="0.6"/><path d="M12 1L17 2L13 6Z" fill="${c.seal}" stroke="#eef2ff" stroke-width="0.5"/><path d="M1 12L3 17L6 13Z" fill="${c.seal}" stroke="#eef2ff" stroke-width="0.5"/>`;
			case "gear": return `<g fill="#b08a3a" stroke="#5a4418" stroke-width="0.6"><path d="M0 0H10A10 10 0 0 1 0 10Z"/><rect x="9" y="-1.5" width="4" height="3" transform="rotate(15)"/><rect x="9" y="-1.5" width="4" height="3" transform="rotate(45)"/><rect x="9" y="-1.5" width="4" height="3" transform="rotate(75)"/></g><circle cx="0" cy="0" r="4" fill="${c.accent}"/>`;
			case "shell": return `<path d="M2 2L13 4A9 9 0 0 1 4 13Z" fill="#efe2d2" stroke="#8a6a5a" stroke-width="0.6"/><path d="M2 2L11 8M2 2L8 11" stroke="#8a6a5a" stroke-width="0.6"/><path d="M0 17Q2 15 4 17T8 17T12 17" fill="none" stroke="${c.accent}" stroke-width="1.2" stroke-linecap="round"/><circle cx="15" cy="4" r="1.4" fill="${c.seal}"/>`;
			default: return `<path d="M0 16Q0 0 16 0" fill="none" stroke="${GOLD2}" stroke-width="1.6"/><path d="M7 2L10 7L7 12L4 7Z" fill="${c.accent}" stroke="#f2eaff" stroke-width="0.6"/>`;
		}
	}
	var CORNER_AT = [
		"tl",
		"tr",
		"bl",
		"br"
	];
	/** 一角的 SVG（`tr` 左右鏡射、`bl` 上下鏡射、`br` 兩個都鏡射）。 */
	function cornerSvg(kind, c, at = "tl") {
		const sx = at === "tr" || at === "br" ? -1 : 1;
		const sy = at === "bl" || at === "br" ? -1 : 1;
		const tx = sx < 0 ? 18 : 0;
		const ty = sy < 0 ? 18 : 0;
		const s = 18;
		return `<svg xmlns="http://www.w3.org/2000/svg" width="${s}" height="${s}" viewBox="0 0 ${s} ${s}"><g transform="translate(${tx} ${ty}) scale(${sx} ${sy})">${cornerShapes(kind, c)}</g></svg>`;
	}
	var POS = {
		tl: `left 2px top 2px`,
		tr: `right 2px top 2px`,
		bl: `left 2px bottom 2px`,
		br: `right 2px bottom 2px`
	};
	/** 四角的 CSS 背景圖層（逗號分隔，給 `background:`）。`scale`：小框（高度 64px 以下）用 0.7（UI-E1 追加 4）。 */
	function cornerLayers(kind, c, scale = 1) {
		const size = Math.round(18 * scale * 10) / 10;
		return CORNER_AT.map((at) => `url("data:image/svg+xml,${encodeURIComponent(cornerSvg(kind, c, at))}") ${POS[at]} / ${size}px ${size}px no-repeat`).join(", ");
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/ui/smallFrames.ts
	/** 小框的飾件縮放。 */
	var SMALL_CORNER_SCALE = .7;
	var WAIT_FX = [
		"none",
		"ember",
		"crystal"
	];
	var ID_RE = /^[a-z][a-z0-9_]*$/;
	var HEX_RE = /^#[0-9a-fA-F]{6}$/;
	var THEME_KEYS = [
		"accent",
		"corner",
		"plaque",
		"portrait_ring",
		"ink",
		"seal",
		"wait_fx"
	];
	var HEX_KEYS = [
		"accent",
		"portrait_ring",
		"ink",
		"seal"
	];
	var isObj = (v) => typeof v === "object" && v !== null && !Array.isArray(v);
	/** 一筆標題牌材質的問題（空＝合法）。 */
	function plaqueProblems(raw) {
		if (!isObj(raw)) return ["不是物件"];
		const p = [];
		for (const k of ["top", "bottom"]) if (typeof raw[k] !== "string" || !HEX_RE.test(raw[k])) p.push(`${k} 必須是 #rrggbb`);
		for (const k of Object.keys(raw)) if (k !== "top" && k !== "bottom") p.push(`未知欄位 ${k}`);
		return p;
	}
	/** 一筆主題的問題（空＝合法）。`plaques`：已知的標題牌材質。 */
	function themeProblems(raw, plaques) {
		if (!isObj(raw)) return ["不是物件"];
		const p = [];
		for (const k of HEX_KEYS) if (typeof raw[k] !== "string" || !HEX_RE.test(raw[k])) p.push(`${k} 必須是 #rrggbb`);
		if (!CORNER_KINDS.includes(raw.corner)) p.push(`未知的 corner：${String(raw.corner)}`);
		if (typeof raw.plaque !== "string" || !plaques.includes(raw.plaque)) p.push(`未知的 plaque：${String(raw.plaque)}`);
		if ("wait_fx" in raw && !WAIT_FX.includes(raw.wait_fx)) p.push(`未知的 wait_fx：${String(raw.wait_fx)}`);
		for (const k of Object.keys(raw)) if (!THEME_KEYS.includes(k)) p.push(`未知欄位 ${k}`);
		return p;
	}
	/** YAML 文字 → 主題表（最上層是 `plaques:` 與 `themes:`）。 */
	function parseRegionThemes(text) {
		const out = {
			plaques: {},
			themes: {},
			errors: []
		};
		let doc;
		try {
			doc = parse(text);
		} catch (e) {
			out.errors.push(`YAML 格式錯誤：${String(e)}`);
			return out;
		}
		const root = isObj(doc) ? doc : {};
		if (!isObj(root.plaques)) out.errors.push("缺少 plaques 對照表");
		else for (const [id, raw] of Object.entries(root.plaques)) {
			const p = ID_RE.test(id) ? plaqueProblems(raw) : ["id 格式錯誤"];
			if (p.length > 0) out.errors.push(`plaques.${id}：${p.join("；")}`);
			else out.plaques[id] = raw;
		}
		if (!isObj(root.themes)) out.errors.push("缺少 themes 對照表");
		else for (const [id, raw] of Object.entries(root.themes)) {
			const p = ID_RE.test(id) ? themeProblems(raw, Object.keys(out.plaques)) : ["id 格式錯誤"];
			if (p.length > 0) out.errors.push(`themes.${id}：${p.join("；")}`);
			else out.themes[id] = raw;
		}
		if (out.themes["hub"] === void 0) out.errors.push(`缺少 hub 主題`);
		return out;
	}
	/** 內建的主題表（build 時匯入）。 */
	var REGION_THEMES = parseRegionThemes(region_themes_default);
	/** 整份檔壞掉時的最後退路（同 yaml 的 hub）。 */
	var HARD_FALLBACK = {
		accent: "#a898ff",
		corner: "filigree",
		plaque: "crystal",
		portrait_ring: "#a898ff",
		ink: "#22305a",
		seal: "#7a5ad0",
		wait_fx: "crystal"
	};
	var HARD_PLAQUE = {
		top: "#2a2a5a",
		bottom: "#1a1a3a"
	};
	/** 該區的主題；`null`、空字串、沒有這區時用 hub。 */
	function regionThemeFor(region, table = REGION_THEMES) {
		const id = region != null && table.themes[region] !== void 0 ? region : "hub";
		const def = table.themes[id] ?? HARD_FALLBACK;
		return {
			...def,
			id,
			wait_fx: def.wait_fx ?? "none",
			plaqueColors: table.plaques[def.plaque] ?? HARD_PLAQUE
		};
	}
	/** 主題 → `<html>` 上的 CSS 變數（`--rt-*`）。 */
	function themeCssVars(theme) {
		return {
			"--rt-accent": theme.accent,
			"--rt-ring": theme.portrait_ring,
			"--rt-ink": theme.ink,
			"--rt-seal": theme.seal,
			"--rt-plaque-top": theme.plaqueColors.top,
			"--rt-plaque-bottom": theme.plaqueColors.bottom,
			"--rt-corners": cornerLayers(theme.corner, theme),
			"--rt-corners-small": cornerLayers(theme.corner, theme, SMALL_CORNER_SCALE)
		};
	}
	var stack = [];
	var current = regionThemeFor(null);
	var swap = 0;
	var swapTimer = null;
	var listeners = /* @__PURE__ */ new Set();
	function apply() {
		const top = stack[stack.length - 1];
		const theme = regionThemeFor(top?.region ?? null);
		if (theme.id === current.id && typeof document !== "undefined" && document.documentElement.dataset.region === theme.id) return;
		current = theme;
		swap += 1;
		if (typeof document !== "undefined") {
			const root = document.documentElement;
			for (const [k, v] of Object.entries(themeCssVars(theme))) root.style.setProperty(k, v);
			root.dataset.region = theme.id;
			root.dataset.rtSwap = swap % 2 === 0 ? "a" : "b";
			if (swapTimer !== null) clearTimeout(swapTimer);
			swapTimer = setTimeout(() => {
				delete root.dataset.rtSwap;
				swapTimer = null;
			}, 400);
		}
		for (const l of [...listeners]) l();
	}
	apply();
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/ui/CreateIcons.tsx
	var GOLD$6 = "#e8bb48";
	var NAVY = "#161a2a";
	/** 有專屬圖樣的區域（其他區用菱形）。 */
	var CREST_REGIONS = [
		"crystal_crown",
		"cloud_ridge",
		"arcane_hub",
		"ashen_waste",
		"frost_tide"
	];
	function crestGlyph(region, c) {
		switch (region) {
			case "crystal_crown": return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M11 25L12 15L16.5 20L20 13L23.5 20L28 15L29 25Z",
				fill: c,
				stroke: "#eef2ff",
				strokeWidth: "0.8",
				strokeLinejoin: "round"
			});
			case "cloud_ridge": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M9 27L16 15L20 21L23 17L31 27Z",
				fill: c,
				stroke: "#e8f4dc",
				strokeWidth: "0.8",
				strokeLinejoin: "round"
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M14 18.5L16 15L18 18.5Z",
				fill: "#f4f8ee"
			})] });
			case "arcane_hub": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("g", {
					fill: c,
					children: [
						0,
						45,
						90,
						135,
						180,
						225,
						270,
						315
					].map((a) => /* @__PURE__ */ (0, import_jsx_runtime.jsx)("rect", {
						x: "18.6",
						y: "10",
						width: "2.8",
						height: "4",
						transform: `rotate(${a} 20 20)`
					}, a))
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
					cx: "20",
					cy: "20",
					r: "6.5",
					fill: c
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("circle", {
					cx: "20",
					cy: "20",
					r: "2.6",
					fill: NAVY
				})
			] });
			case "ashen_waste": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)(import_jsx_runtime.Fragment, { children: [/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M20 10C24 15 27 18 26 23A6 6 0 0 1 14 23C13.5 19.5 16 18 17 15C18 18 19.5 18.5 20 10Z",
				fill: c
			}), /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M20 19C22 21.5 22.5 23 21.8 24.5A2.2 2.2 0 0 1 18.2 24.5C17.8 23 18.8 21.5 20 19Z",
				fill: "#ffe08a"
			})] });
			case "frost_tide": return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("g", {
				fill: "none",
				stroke: c,
				strokeWidth: "2",
				strokeLinecap: "round",
				children: [
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M11 16Q13.5 13.5 16 16T21 16T26 16T29 16" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M11 21Q13.5 18.5 16 21T21 21T26 21T29 21" }),
					/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", { d: "M13 26Q15.5 23.5 18 26T23 26T27 26" })
				]
			});
			default: return /* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
				d: "M20 12L27 20L20 28L13 20Z",
				fill: c
			});
		}
	}
	/** 出身的區域紋章：六角金框、深藍底、區域色圖樣。 */
	function RegionCrest({ region, size = 34 }) {
		const c = regionThemeFor(region).accent;
		return /* @__PURE__ */ (0, import_jsx_runtime.jsxs)("svg", {
			className: "region-crest",
			viewBox: "0 0 40 40",
			width: size,
			height: size,
			"aria-hidden": "true",
			"data-crest": region,
			children: [
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M20 2L35.6 11V29L20 38L4.4 29V11Z",
					fill: NAVY,
					stroke: GOLD$6,
					strokeWidth: "1.6",
					strokeLinejoin: "round"
				}),
				/* @__PURE__ */ (0, import_jsx_runtime.jsx)("path", {
					d: "M20 5.5L32.6 12.8V27.2L20 34.5L7.4 27.2V12.8Z",
					fill: "none",
					stroke: c,
					strokeOpacity: "0.55",
					strokeWidth: "0.8"
				}),
				crestGlyph(region, c)
			]
		});
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/palette.ts
	var ELEMENT_COLORS = {
		physical: {
			name: "物理",
			primary: "#f2f2f2",
			secondary: "#b8bcc8",
			accent: "#e8ebf0",
			dark: "#2c313b",
			light: "#7d8798",
			bright: "#ffffff",
			mark: "#e05050"
		},
		fire: {
			name: "火",
			primary: "#ff6a1a",
			secondary: "#ffd23f",
			accent: "#ffb23a",
			dark: "#4a1104",
			light: "#e8541a",
			bright: "#ffd04a"
		},
		ice: {
			name: "冰",
			primary: "#8fe3ff",
			secondary: "#ffffff",
			accent: "#d8f6ff",
			dark: "#0b2f4e",
			light: "#3fa6d8",
			bright: "#e8fbff"
		},
		lightning: {
			name: "雷",
			primary: "#fff36b",
			secondary: "#8fd0ff",
			accent: "#fff36b",
			dark: "#1d1d4a",
			light: "#5a5ac8",
			bright: "#fff7c0"
		},
		poison: {
			name: "毒",
			primary: "#7ddc3a",
			secondary: "#3f8f2a",
			accent: "#b6f06a",
			dark: "#12320c",
			light: "#4f9a28",
			bright: "#d6f59a"
		},
		wind: {
			name: "風",
			primary: "#c8ffe8",
			secondary: "#7fe0c0",
			accent: "#dcfff1",
			dark: "#0b3f3a",
			light: "#3fb59a",
			bright: "#effff8"
		},
		earth: {
			name: "大地",
			primary: "#b0814a",
			secondary: "#6e5236",
			accent: "#f0c890",
			dark: "#2e1d0e",
			light: "#9a6a36",
			bright: "#e6c89a"
		},
		holy: {
			name: "聖光",
			primary: "#fff2b0",
			secondary: "#ffd75e",
			accent: "#fff6c8",
			dark: "#5a3a06",
			light: "#e7b23a",
			bright: "#fffbe0"
		},
		shadow: {
			name: "暗影",
			primary: "#9a6ad8",
			secondary: "#2a1840",
			accent: "#d2b0ff",
			dark: "#10071e",
			light: "#5a3590",
			bright: "#c8a8f0"
		}
	};
	/** 水不是元素（只是表面與「濕」關鍵字）；保留一個水色，若之後內容加入水元素可直接放進 `ELEMENT_COLORS`。 */
	var WATER_COLOR = "#4aa8ff";
	/** 沒有元素、不認得的元素。 */
	var NEUTRAL_COLOR = "#d8d8e0";
	/** 元素的代表色（狀態圖樣、腳邊粒子、陷阱與區域）；水＝水色，不認得 → 中性色。 */
	function elementColor(el) {
		if (el == null) return NEUTRAL_COLOR;
		if (el === "water") return WATER_COLOR;
		const c = ELEMENT_COLORS[el];
		return c === void 0 ? NEUTRAL_COLOR : c.mark ?? c.primary;
	}
	ELEMENT_COLORS["fire"].primary, ELEMENT_COLORS["lightning"].primary, ELEMENT_COLORS["ice"].primary;
	/** 技能圖示上「表面」小圖樣的顏色（畫在深色底上，偏亮）；火取元素色。 */
	var SURFACE_ICON_COLOR = {
		fire: ELEMENT_COLORS["fire"].primary,
		ice: "#cdeeff",
		oil: "#5a4a30",
		water: "#4a9af0",
		holy: "#ffe58a",
		darkness: "#8a5ad0",
		smoke: "#c0c0c8",
		poison: "#86d84a"
	};
	/** 戰場上表面蓋在地形上的顏色（半透明疊色，偏暗）；火取元素色。 */
	var SURFACE_GROUND_COLOR = {
		oil: "#2b2416",
		water: "#3a7bd5",
		fire: ELEMENT_COLORS["fire"].primary,
		ice: "#c8ecff",
		poison: "#7bc043",
		holy: "#fff1a8",
		darkness: "#3b1f4f",
		smoke: "#b8b8c0"
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/battle/glossary.ts
	var index = /* @__PURE__ */ new Map();
	function glossaryEntry(category, id) {
		return index.get(category)?.get(id);
	}
	/** 中文名；對照表沒有時顯示 ID。 */
	function glossaryName(category, id) {
		return glossaryEntry(category, id)?.name_zh ?? id;
	}
	var statusName = (id) => glossaryName("statuses", id);
	/** 狀態圖示與身上特效用的欄位（`/api/glossary` 的 `status_look`）；沒有資料時為 `undefined`。 */
	var statusLook = (id) => glossaryEntry("statuses", id)?.status_look ?? void 0;
	/** 表面的顏色取自 `render/palette.ts`（單一來源），這裡只決定疊色比例。 */
	var ground = (id, alpha) => ({
		color: parseInt((SURFACE_GROUND_COLOR[id] ?? "#888888").slice(1), 16),
		alpha
	});
	ground("oil", .6), ground("water", .55), ground("fire", .7), ground("ice", .7), ground("poison", .6), ground("holy", .6), ground("darkness", .65), ground("smoke", .6);
	Object.freeze({});
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/material.ts
	/** 材質 → [主色, 暗色]；不認得的材質用布料色。 */
	var MATERIAL = {
		cloth: ["#8a8f99", "#5d6168"],
		leather: ["#8a5a32", "#5e3b1f"],
		iron: ["#7a828b", "#474c52"],
		steel: ["#a9b6c6", "#6d7a8a"],
		gold: ["#e8bb48", "#9c7420"],
		wood: ["#a06a36", "#6a4420"],
		bone: ["#e9e3cf", "#a8a08a"],
		copper: ["#b06a3c", "#6e3e20"],
		silver: ["#e8edf2", "#a8b0ba"],
		crystal: ["#b8a8ff", "#7a68c8"]
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/inkStyle.ts
	/**
	* 墨線畫風共用的材質色（Phase 3T-4）。金、木取自 `appearance.MATERIAL`（同一份）；
	* 鋼、鐵是墨線畫風專用的較亮金屬色（美術 PM 定案，與 `MATERIAL` 的 steel／iron 不同，改了會動所有小人的盔甲與劍）。
	*/
	var MAT = {
		steel: "#c3ccd6",
		iron: "#8d969f",
		gold: MATERIAL["gold"][0],
		wood: MATERIAL["wood"][0]
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/attackVariants.ts
	var PI$2 = Math.PI;
	/** 由上往下（6N-5 以前唯一的弧光）。 */
	var ARC_DOWN = {
		kind: "arc",
		from: -.45 * PI$2,
		sweep: .9 * PI$2
	};
	var ARC_UP = {
		kind: "arc",
		from: .45 * PI$2,
		sweep: -.9 * PI$2
	};
	var ARC_ACROSS = {
		kind: "arc",
		from: .95 * PI$2,
		sweep: -.9 * PI$2,
		squash: .42
	};
	var ARC_RING = {
		kind: "ring",
		from: .5 * PI$2,
		sweep: -2 * PI$2,
		squash: .5
	};
	var line$1 = (angle) => ({
		kind: "line",
		angle
	});
	var REST$1 = {
		arm: 0,
		wpn: .75
	};
	var fx$2 = (kind, where, from = 0, to = 1) => ({
		kind,
		where,
		from,
		to
	});
	var STANCE = {
		hipN: .45,
		hipF: -.3
	};
	var LO = {
		arm: .9,
		wpn: -3.3,
		lean: -.1,
		hipN: .25,
		hipF: -.2,
		bob: 1.5
	};
	var SIDE = {
		arm: -1.2,
		wpn: -.4,
		lean: -.12,
		hipN: .2
	};
	var THRUST_BACK = {
		arm: .4,
		elbow: -1.2,
		wpn: 2.4,
		lean: -.08,
		hipN: .2
	};
	var HOP_IN = {
		arm: -2.7,
		wpn: 1.6,
		lean: -.05,
		kneeN: .7,
		kneeF: .7,
		bob: 2.5
	};
	var DRAW_IN = {
		arm: .6,
		elbow: -.9,
		wpn: -2.2,
		lean: .1,
		kneeN: .5,
		kneeF: .3,
		bob: 1.5
	};
	var TWIST = {
		arm: -1,
		wpn: -.4,
		lean: -.2,
		hipN: -.2,
		hipF: .3
	};
	var RUNE_UP = {
		arm: -2.9,
		wpn: 2.9,
		lean: -.06,
		bob: -.6
	};
	var CLEAVE_IN = {
		arm: -2.9,
		elbow: -.2,
		wpn: 2.4,
		armF: -2.6,
		lean: -.18,
		hipN: .3,
		hipF: -.25,
		bob: -.5
	};
	var HEAVY_SIDE = {
		arm: -1,
		wpn: -.5,
		armF: -1,
		lean: -.2,
		hipN: -.1,
		hipF: .25
	};
	var WHIRL_IN = {
		arm: -.2,
		wpn: -1.8,
		armF: -.2,
		lean: -.15,
		kneeN: .4,
		bob: 1
	};
	var STAB_IN = {
		arm: .4,
		elbow: -1.3,
		wpn: 2.4,
		armF: .3,
		elbowF: -1.3,
		lean: -.08
	};
	var PAIR_TWIST = {
		arm: -.9,
		wpn: -.5,
		armF: -.6,
		lean: -.2,
		hipN: -.2,
		hipF: .3
	};
	var BACKHAND_IN = {
		arm: -2.6,
		elbow: -.4,
		wpn: 6,
		armF: -1.2,
		lean: -.1
	};
	var LOW_IN = {
		arm: .6,
		wpn: 1.3,
		lean: .05,
		kneeN: .6,
		kneeF: .5,
		bob: 2
	};
	var SPEAR_SIDE = {
		arm: -1.3,
		wpn: -.3,
		lean: -.15,
		hipN: .2
	};
	var LEAP_IN = {
		arm: -2.2,
		wpn: 3,
		lean: -.05,
		kneeN: .8,
		kneeF: .8,
		bob: 2.5
	};
	var SCY_LIFT_IN = {
		arm: .6,
		wpn: -2.8,
		lean: -.1,
		kneeN: .4,
		bob: 1.2
	};
	var WHIP_UP_IN = {
		arm: .5,
		wpn: -2.4,
		lean: -.1,
		kneeN: .3,
		bob: 1
	};
	var WHIP_IN = {
		arm: -2.6,
		wpn: .4,
		lean: -.15
	};
	var WRAP_IN = {
		arm: -2,
		wpn: -.6,
		lean: -.1
	};
	var wind = (ms, to, extra = {}) => ({
		ms,
		anchor: "tip",
		keys: [[0, REST$1], [1, to]],
		...extra
	});
	var HOOK_IN = {
		arm: .1,
		elbow: -1.9,
		lean: -.15,
		hipN: -.15,
		hipF: .25
	};
	var UPPER_IN = {
		arm: .7,
		elbow: -1.5,
		lean: .08,
		kneeN: .5,
		kneeF: .4,
		bob: 2.2
	};
	var KNEE_IN = {
		arm: -.7,
		elbow: -1.5,
		armF: -.7,
		elbowF: -1.5,
		lean: -.05
	};
	var KICK_IN = {
		arm: -.6,
		elbow: -1.4,
		armF: .3,
		lean: -.25,
		hipN: -.2,
		hipF: .3
	};
	var AIM$1 = {
		arm: -1.3,
		wpn: 2.87,
		lean: -.05
	};
	/** 半蹲射：膝蓋彎、身體往下沉。 */
	var BOW_CROUCH = {
		kneeN: .9,
		kneeF: .7,
		hipN: .45,
		hipF: .1,
		bob: 4,
		lean: .06
	};
	/** 側身射：上半身往後仰、轉開。 */
	var BOW_SIDE = {
		lean: -.14,
		hipN: -.25,
		hipF: .35,
		arm: .05
	};
	/** 拋射：弓往上抬約 45 度（武器絕對角度 ≈ π/4）。 */
	var BOW_LOB = {
		arm: -.6,
		wpn: -.2,
		lean: -.15
	};
	/** 腰射：手放低、手肘彎，槍身仍水平（arm＋elbow＋wpn 不變）。 */
	var GUN_HIP = {
		arm: .8,
		elbow: -.85,
		wpn: .05,
		lean: .05
	};
	/** 單膝射：前腳跪下。 */
	var GUN_KNEEL = {
		kneeN: 1.6,
		hipN: 1,
		kneeF: .4,
		bob: 5,
		lean: .05
	};
	/** 姿勢逐欄相加（遠程變體 ＝ 原本的瞄準、放箭姿勢 ＋ 一組差值，後座的形狀跟著原本的）。 */
	function plus$2(p, d) {
		const out = { ...p };
		for (const [k, v] of Object.entries(d)) out[k] = (p[k] ?? 0) + v;
		return out;
	}
	/**
	* 遠程變體的蓄力＋出招：照起手對照表的弓（aim／release）或弩、火槍（aim_gun／fire）的關鍵點，每個姿勢加上 `delta`
	* （開頭的站好不加），後座那一格（0.15）再加 `kick`。長度、`hitAt`、特效（火槍的槍口火光）都和原本的一樣。
	*/
	function rangedPair(name, base, delta, kick) {
		const a = plus$2(AIM$1, delta);
		const windup = base === "bow" ? {
			ms: 360,
			anchor: "tip",
			keys: [
				[0, REST$1],
				[.6, a],
				[1, {
					...a,
					pull: 6
				}]
			]
		} : {
			ms: 340,
			anchor: "tip",
			keys: [
				[0, REST$1],
				[.7, a],
				[1, a]
			]
		};
		const strike = base === "bow" ? {
			ms: 300,
			anchor: "tip",
			hitAt: .15,
			keys: [
				[0, {
					...a,
					pull: 6
				}],
				[.15, plus$2(plus$2({
					arm: -1.45,
					wpn: 2.77,
					lean: -.08,
					pull: 0
				}, delta), kick)],
				[1, {
					...a,
					pull: 0
				}]
			]
		} : {
			ms: 260,
			anchor: "tip",
			hitAt: .15,
			keys: [
				[0, a],
				[.15, plus$2(plus$2({
					arm: -1.6,
					wpn: 2.77,
					lean: -.12
				}, delta), kick)],
				[1, a]
			],
			fx: [fx$2("muzzle", "anchor", .1, .45)]
		};
		return {
			[`${name}_in`]: windup,
			[name]: strike
		};
	}
	wind(260, LO), { ...STANCE }, { ...STANCE }, wind(260, SIDE), { ...STANCE }, { ...STANCE }, wind(260, THRUST_BACK), wind(260, HOP_IN), wind(260, DRAW_IN), wind(260, TWIST), { ...STANCE }, { ...STANCE }, wind(280, SIDE, { fx: [fx$2("glow", "anchor", .3, 1)] }), wind(280, THRUST_BACK, { fx: [fx$2("glow", "anchor", .3, 1)] }), wind(280, RUNE_UP, { fx: [fx$2("glow", "anchor", .2, 1), fx$2("sigil", "anchor", .45, 1)] }), { ...STANCE }, { ...STANCE }, wind(260, CLEAVE_IN), wind(260, HEAVY_SIDE), { ...STANCE }, { ...STANCE }, wind(260, WHIRL_IN), { ...STANCE }, { ...STANCE }, wind(260, STAB_IN), { ...STANCE }, { ...STANCE }, wind(260, PAIR_TWIST), { ...STANCE }, { ...STANCE }, wind(260, BACKHAND_IN), { ...STANCE }, { ...STANCE }, wind(220, LOW_IN), wind(220, SPEAR_SIDE), { ...STANCE }, { ...STANCE }, wind(220, LEAP_IN), wind(260, SIDE), wind(260, SCY_LIFT_IN), wind(260, TWIST), { ...STANCE }, { ...STANCE }, wind(240, WHIP_UP_IN), wind(240, WHIP_IN), wind(240, WRAP_IN), wind(200, HOOK_IN, { anchor: "hand" }), { ...STANCE }, { ...STANCE }, wind(200, UPPER_IN, { anchor: "hand" }), wind(200, KNEE_IN, { anchor: "chest" }), wind(200, KICK_IN, { anchor: "feet" }), {
		...rangedPair("bow_crouch", "bow", BOW_CROUCH, {}),
		...rangedPair("bow_side", "bow", BOW_SIDE, { lean: -.03 }),
		...rangedPair("bow_lob", "bow", BOW_LOB, { arm: -.05 }),
		...rangedPair("gun_hip", "gun", GUN_HIP, { elbow: -.15 }),
		...rangedPair("gun_kneel", "gun", GUN_KNEEL, { lean: -.04 })
	};
	var v = (id, zh, windup, strike, swing, arc) => ({
		id,
		zh,
		windup,
		strike,
		swing,
		arc
	});
	/**
	* 變體表（方案 2.10 第 5 點的例子）。每列第一個 ＝ 6N-6 以前的普攻（起手對照表的近身那一欄），弧光照舊由上往下或照揮的方向。
	*/
	var MELEE_VARIANTS = {
		sword: [
			v("sword_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
			v("sword_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
			v("sword_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
			v("sword_thrust", "突刺", "sword_thrust_in", "sword_thrust", "thrust", line$1(0)),
			v("sword_hop", "小跳斬", "hop_in", "hop_slash", "down", {
				kind: "arc",
				from: -.55 * PI$2,
				sweep: .8 * PI$2
			})
		],
		saber: [
			v("saber_down", "由上往下", "windup", "slash", "down", ARC_DOWN),
			v("saber_up", "由下往上", "windup_lo", "slash_lo", "up", ARC_UP),
			v("saber_across", "橫掃", "windup_side", "slash_side", "across", ARC_ACROSS),
			v("saber_draw", "拔刀斬", "draw_in", "draw_slash", "up", {
				kind: "arc",
				from: .6 * PI$2,
				sweep: -.75 * PI$2
			}),
			v("saber_spin", "迴身斬", "spin_in", "spin_slash", "spin", ARC_RING)
		],
		arcane: [
			v("arcane_down", "由上往下", "arcane_windup", "slash", "down", ARC_DOWN),
			v("arcane_across", "橫掃", "arcane_side_in", "slash_side", "across", ARC_ACROSS),
			v("arcane_thrust", "突刺", "arcane_thrust_in", "sword_thrust", "thrust", line$1(0)),
			v("arcane_rune", "符文一亮再斬", "rune_in", "rune_slash", "down", {
				kind: "arc",
				from: -.5 * PI$2,
				sweep: .75 * PI$2
			})
		],
		heavy: [
			v("heavy_cleave", "劈", "cleave_in", "cleave", "down", {
				kind: "arc",
				from: -.55 * PI$2,
				sweep: .85 * PI$2
			}),
			v("heavy_across", "橫掃", "heavy_side_in", "heavy_sweep", "across", ARC_ACROSS),
			v("heavy_whirl", "掄一圈", "whirl_in", "whirl", "spin", {
				kind: "ring",
				from: PI$2,
				sweep: 2 * PI$2,
				squash: 1
			})
		],
		pair: [
			v("pair_cross", "交叉斬", "x_windup", "twin_slash", "down", {
				kind: "cross",
				angle: .3 * PI$2,
				angle2: .7 * PI$2
			}),
			v("pair_stab", "連刺", "pair_stab_in", "pair_stab", "thrust", line$1(0)),
			v("pair_spin", "迴旋", "pair_spin_in", "pair_spin", "spin", ARC_RING),
			v("pair_backhand", "反手刺", "backhand_in", "backhand_stab", "down", line$1(.4 * PI$2))
		],
		spear: [
			v("spear_thrust", "直刺", "thrust_in", "thrust", "thrust", line$1(0)),
			v("spear_low", "下段刺", "low_thrust_in", "low_thrust", "thrust", line$1(.15 * PI$2)),
			v("spear_across", "橫掃", "spear_side_in", "spear_sweep", "across", ARC_ACROSS),
			v("spear_leap", "跳刺", "leap_thrust_in", "leap_thrust", "thrust", line$1(.3 * PI$2))
		],
		scythe: [
			v("scythe_across", "橫掃", "scythe_side_in", "sweep", "across", ARC_ACROSS),
			v("scythe_lift", "上挑", "scythe_lift_in", "scythe_lift", "up", ARC_UP),
			v("scythe_spin", "迴旋", "scythe_spin_in", "scythe_spin", "spin", ARC_RING)
		],
		whip: [
			v("whip_up", "上甩", "whip_up_in", "whip_up", "up", ARC_UP),
			v("whip_side", "側甩", "whip_side_in", "whip_lash", "across", ARC_ACROSS),
			v("whip_wrap", "纏繞拉扯", "whip_wrap_in", "whip_wrap", "spin", ARC_RING)
		]
	};
	/** 6N-7 的列（每列第一個 ＝ 6N-7 以前的普攻：拳套空手照近身那一欄，弓、弩、火槍照遠程那一欄）。 */
	var MORE_VARIANTS = {
		fist: [
			v("fist_jab", "直拳", "fist_in", "punch", "thrust", line$1(0)),
			v("fist_hook", "勾拳", "hook_in", "hook", "across", ARC_ACROSS),
			v("fist_upper", "上勾拳", "upper_in", "uppercut", "up", ARC_UP),
			v("fist_knee", "膝撞", "knee_in", "knee_strike", "up", line$1(-.3 * PI$2)),
			v("fist_kick", "迴旋踢", "kick_in", "spin_kick", "spin", ARC_RING)
		],
		bow: [
			v("bow_stand", "站射", "aim", "release", "shoot", null),
			v("bow_crouch", "半蹲射", "bow_crouch_in", "bow_crouch", "shoot", null),
			v("bow_side", "側身射", "bow_side_in", "bow_side", "shoot", null),
			v("bow_lob", "拋射", "bow_lob_in", "bow_lob", "shoot", null)
		],
		crossbow: [
			v("crossbow_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
			v("crossbow_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
			v("crossbow_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null)
		],
		gun: [
			v("gun_shoulder", "抵肩射", "aim_gun", "fire", "shoot", null),
			v("gun_hip", "腰射", "gun_hip_in", "gun_hip", "shoot", null),
			v("gun_kneel", "單膝射", "gun_kneel_in", "gun_kneel", "shoot", null)
		]
	};
	({
		...MELEE_VARIANTS,
		...MORE_VARIANTS
	});
	Object.freeze({
		hipN: .35,
		kneeN: .55,
		hipF: .1,
		kneeF: .3,
		arm: -1.9,
		elbow: -.3,
		armF: -1.5,
		liftL: 1.5,
		armL: -1.2,
		armR: -1.2
	});
	Object.freeze({
		hipN: .45,
		kneeN: .15,
		hipF: -.35,
		kneeF: .35,
		arm: -1.1,
		armF: -.9,
		elbow: -.2,
		liftL: 1.2,
		armL: -1.4,
		armR: -1.4
	});
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/color.ts
	var HEX = /^#[0-9a-f]{6}$/i;
	/** `#rrggbb` → [r, g, b]（0–255）。 */
	function hexRgb(h) {
		const n = parseInt(h.slice(1), 16);
		return [
			n >> 16 & 255,
			n >> 8 & 255,
			n & 255
		];
	}
	/** 兩色混合（`t` ＝ b 的比例）；任一個不是 `#rrggbb` 時原樣回傳 `a`。 */
	function mix(a, b, t) {
		if (!HEX.test(a) || !HEX.test(b)) return a;
		const [r1, g1, b1] = hexRgb(a);
		const [r2, g2, b2] = hexRgb(b);
		const m = (x, y) => Math.round(x * (1 - t) + y * t);
		return `#${(m(r1, r2) << 16 | m(g1, g2) << 8 | m(b1, b2)).toString(16).padStart(6, "0")}`;
	}
	Object.fromEntries(Object.entries(MATERIAL).map(([id, c]) => [id, id === "silver" ? {
		c,
		shine: true
	} : { c }]));
	var gearAppearance_default = {
		styles: ["common"],
		materials: [
			"iron",
			"steel",
			"copper",
			"silver",
			"gold",
			"wood",
			"leather",
			"cloth",
			"bone",
			"crystal"
		],
		dyes: [
			"red",
			"blue",
			"green",
			"purple",
			"black",
			"white",
			"brown",
			"gold"
		],
		dyeMaterials: ["cloth", "leather"],
		rarities: [
			"common",
			"uncommon",
			"rare",
			"epic",
			"legendary"
		],
		maxKeywords: 2,
		keywords: [
			"ignite",
			"wet",
			"charged",
			"frozen",
			"prone",
			"collision",
			"marked",
			"high_ground",
			"concealed",
			"summon",
			"poisoned",
			"form"
		],
		elementKeywords: [
			"ignite",
			"wet",
			"charged",
			"frozen"
		],
		kinds: [
			{
				"id": "sword",
				"slotType": "weapon",
				"zh": "劍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "straight",
						"zh": "直劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "curved",
						"zh": "彎刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "broad",
						"zh": "闊劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "arcane",
						"zh": "魔導劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "greatsword",
				"slotType": "weapon",
				"zh": "巨劍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "twohand",
						"zh": "雙手劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "zhanma",
						"zh": "斬馬刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "serrated",
						"zh": "鋸齒巨劍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "dagger",
				"slotType": "weapon",
				"zh": "匕首",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "short",
						"zh": "短刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "stiletto",
						"zh": "三稜刺",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "kris",
						"zh": "彎匕",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "axe",
				"slotType": "weapon",
				"zh": "斧",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "hand",
						"zh": "手斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "battle",
						"zh": "戰斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "double",
						"zh": "雙刃斧",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "hammer",
				"slotType": "weapon",
				"zh": "錘",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "mace",
						"zh": "釘頭錘",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "warhammer",
						"zh": "戰錘",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "flail",
						"zh": "連枷",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "spear",
				"slotType": "weapon",
				"zh": "矛",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"wood"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "spear",
						"zh": "長矛",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "halberd",
						"zh": "戟",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "trident",
						"zh": "三叉戟",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"wood"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "bow",
				"slotType": "weapon",
				"zh": "弓",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "short",
						"zh": "短弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "long",
						"zh": "長弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "recurve",
						"zh": "反曲弓",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "crossbow",
				"slotType": "weapon",
				"zh": "弩",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "light",
						"zh": "輕弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "heavy",
						"zh": "重弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "repeater",
						"zh": "連弩",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "longgun",
				"slotType": "weapon",
				"zh": "火槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發火槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "hunting",
						"zh": "獵槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "sniper",
						"zh": "狙擊火槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "shotgun",
				"slotType": "weapon",
				"zh": "霰彈槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "blunderbuss",
						"zh": "喇叭槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "double",
						"zh": "雙管",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "pump",
						"zh": "泵動",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "pistol",
				"slotType": "weapon",
				"zh": "手槍",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發手槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "revolver",
						"zh": "左輪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "derringer",
						"zh": "短銃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "dual_pistol",
				"slotType": "weapon",
				"zh": "雙手槍",
				"paired": true,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [
					{
						"id": "flintlock",
						"zh": "燧發手槍",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "revolver",
						"zh": "左輪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					},
					{
						"id": "derringer",
						"zh": "短銃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "steel"
					}
				]
			},
			{
				"id": "fist",
				"slotType": "weapon",
				"zh": "拳套",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"leather"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "katar",
						"zh": "拳刃",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "knuckle",
						"zh": "鐵拳",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "claw",
						"zh": "爪",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"leather"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "scythe",
				"slotType": "weapon",
				"zh": "鐮刀",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "long",
						"zh": "長柄鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "crescent",
						"zh": "彎月鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "hook",
						"zh": "鉤鐮",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "whip",
				"slotType": "weapon",
				"zh": "鞭",
				"paired": false,
				"materials": [
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone"
				],
				"defaultMaterial": "leather",
				"forms": [
					{
						"id": "leather",
						"zh": "皮鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					},
					{
						"id": "chain",
						"zh": "鏈鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					},
					{
						"id": "bladed",
						"zh": "蛇骨鞭",
						"materials": [
							"leather",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone"
						],
						"defaultMaterial": "leather"
					}
				]
			},
			{
				"id": "dual_dagger",
				"slotType": "weapon",
				"zh": "雙匕首",
				"paired": true,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "short",
						"zh": "短刀",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "stiletto",
						"zh": "三稜刺",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "kris",
						"zh": "彎匕",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "staff",
				"slotType": "weapon",
				"zh": "杖",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "wood",
				"forms": [
					{
						"id": "long",
						"zh": "長杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "scepter",
						"zh": "權杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "wand",
						"zh": "短杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					},
					{
						"id": "totem",
						"zh": "圖騰杖",
						"materials": [
							"wood",
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "wood"
					}
				]
			},
			{
				"id": "round_shield",
				"slotType": "offhand",
				"zh": "圓盾",
				"paired": false,
				"materials": [
					"wood",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "wood",
				"forms": [{
					"id": "wood",
					"zh": "木圓盾",
					"materials": [
						"wood",
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "wood"
				}, {
					"id": "banded",
					"zh": "包鐵圓盾",
					"materials": [
						"wood",
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "wood"
				}]
			},
			{
				"id": "kite_shield",
				"slotType": "offhand",
				"zh": "鳶盾",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "kite",
					"zh": "鳶盾",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "tower",
					"zh": "塔盾",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "tome",
				"slotType": "offhand",
				"zh": "法書",
				"paired": false,
				"materials": ["leather", "cloth"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "book",
					"zh": "典籍",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}, {
					"id": "scroll",
					"zh": "卷軸匣",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "orb",
				"slotType": "offhand",
				"zh": "法器珠",
				"paired": false,
				"materials": ["crystal", "bone"],
				"defaultMaterial": "crystal",
				"forms": [{
					"id": "ball",
					"zh": "水晶球",
					"materials": ["crystal", "bone"],
					"defaultMaterial": "crystal"
				}, {
					"id": "floating",
					"zh": "浮空寶珠",
					"materials": ["crystal", "bone"],
					"defaultMaterial": "crystal"
				}]
			},
			{
				"id": "robe",
				"slotType": "body",
				"zh": "布袍",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "long",
					"zh": "長袍",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "short",
					"zh": "短袍",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "leather",
				"slotType": "body",
				"zh": "皮甲",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "vest",
					"zh": "皮背心",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "hunter",
					"zh": "獵裝",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "mail",
				"slotType": "body",
				"zh": "鎖甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "chain",
					"zh": "鎖子甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "scale",
					"zh": "鱗甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "plate",
				"slotType": "body",
				"zh": "板甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "half",
					"zh": "半身板甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "full",
					"zh": "全身板甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "coat",
				"slotType": "body",
				"zh": "外套",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "travel",
					"zh": "旅行外套",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "cape",
					"zh": "披風外套",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "hood",
				"slotType": "head",
				"zh": "兜帽",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "cloth",
					"zh": "布兜帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "cowl",
					"zh": "斗篷帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "hat",
				"slotType": "head",
				"zh": "帽子",
				"paired": false,
				"materials": ["cloth", "leather"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "wizard",
					"zh": "法師帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "wide",
					"zh": "寬簷帽",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "circlet",
				"slotType": "head",
				"zh": "頭巾／頭冠",
				"paired": false,
				"materials": [
					"cloth",
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "bandana",
					"zh": "頭巾",
					"materials": ["cloth", "leather"],
					"defaultMaterial": "cloth"
				}, {
					"id": "crown",
					"zh": "頭冠",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}]
			},
			{
				"id": "cap",
				"slotType": "head",
				"zh": "皮帽",
				"paired": false,
				"materials": ["leather", "cloth"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "leather",
					"zh": "皮帽",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}, {
					"id": "fur",
					"zh": "毛帽",
					"materials": ["leather", "cloth"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "helmet",
				"slotType": "head",
				"zh": "頭盔",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [
					{
						"id": "iron",
						"zh": "鐵盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "horned",
						"zh": "角盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					},
					{
						"id": "greathelm",
						"zh": "全罩盔",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold"
						],
						"defaultMaterial": "iron"
					}
				]
			},
			{
				"id": "cloth_gloves",
				"slotType": "hands",
				"zh": "布手套",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "plain",
					"zh": "素手套",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "fingerless",
					"zh": "露指手套",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "leather_gloves",
				"slotType": "hands",
				"zh": "皮手套",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "short",
					"zh": "短皮手套",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "long",
					"zh": "長皮手套",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "gauntlets",
				"slotType": "hands",
				"zh": "護手",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "plate",
					"zh": "板金護手",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "mail",
					"zh": "鎖鏈護手",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "bracers",
				"slotType": "hands",
				"zh": "臂甲",
				"paired": false,
				"materials": [
					"leather",
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "leather",
					"zh": "皮臂甲",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "ring",
					"zh": "臂環",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "copper"
				}]
			},
			{
				"id": "shoes",
				"slotType": "feet",
				"zh": "布鞋",
				"paired": false,
				"materials": ["cloth"],
				"defaultMaterial": "cloth",
				"forms": [{
					"id": "slipper",
					"zh": "布鞋",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}, {
					"id": "wrapped",
					"zh": "綁腿鞋",
					"materials": ["cloth"],
					"defaultMaterial": "cloth"
				}]
			},
			{
				"id": "boots",
				"slotType": "feet",
				"zh": "皮靴",
				"paired": false,
				"materials": ["leather"],
				"defaultMaterial": "leather",
				"forms": [{
					"id": "short",
					"zh": "短靴",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}, {
					"id": "tall",
					"zh": "長靴",
					"materials": ["leather"],
					"defaultMaterial": "leather"
				}]
			},
			{
				"id": "iron_boots",
				"slotType": "feet",
				"zh": "鐵靴",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "iron",
				"forms": [{
					"id": "plain",
					"zh": "鐵靴",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}, {
					"id": "sabaton",
					"zh": "尖頭鐵靴",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "iron"
				}]
			},
			{
				"id": "greaves",
				"slotType": "feet",
				"zh": "脛甲",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold"
				],
				"defaultMaterial": "steel",
				"forms": [{
					"id": "plain",
					"zh": "脛甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}, {
					"id": "knee",
					"zh": "護膝脛甲",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold"
					],
					"defaultMaterial": "steel"
				}]
			},
			{
				"id": "ring",
				"slotType": "ring",
				"zh": "戒指",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "gold",
				"forms": [
					{
						"id": "plain",
						"zh": "素戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					},
					{
						"id": "gem",
						"zh": "寶石戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					},
					{
						"id": "signet",
						"zh": "印戒",
						"materials": [
							"iron",
							"steel",
							"copper",
							"silver",
							"gold",
							"bone",
							"crystal"
						],
						"defaultMaterial": "gold"
					}
				]
			},
			{
				"id": "pendant",
				"slotType": "neck",
				"zh": "墜飾",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal"
				],
				"defaultMaterial": "gold",
				"forms": [{
					"id": "pendant",
					"zh": "項鍊墜",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}, {
					"id": "tag",
					"zh": "吊牌",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal"
					],
					"defaultMaterial": "gold"
				}]
			},
			{
				"id": "charm",
				"slotType": "neck",
				"zh": "護符",
				"paired": false,
				"materials": [
					"iron",
					"steel",
					"copper",
					"silver",
					"gold",
					"bone",
					"crystal",
					"leather",
					"cloth"
				],
				"defaultMaterial": "gold",
				"forms": [{
					"id": "tablet",
					"zh": "符牌",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal",
						"leather",
						"cloth"
					],
					"defaultMaterial": "gold"
				}, {
					"id": "bone",
					"zh": "骨符",
					"materials": [
						"iron",
						"steel",
						"copper",
						"silver",
						"gold",
						"bone",
						"crystal",
						"leather",
						"cloth"
					],
					"defaultMaterial": "gold"
				}]
			}
		]
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/qIcon/core.ts
	var TAU$3 = Math.PI * 2;
	/** 剪影外框色（和 Q 版人物 `Q_OUT` 同色）。 */
	var OUT = "#16121a";
	var mat$1 = (id) => MATERIAL[id];
	/** 畫法固定零件的顏色。鋼、鐵、木、皮照 `material.ts`（第 0.0 節第 3 點）；其餘照樣張。 */
	var M = {
		steel: mat$1("steel")[0],
		steelD: mat$1("steel")[1],
		iron: mat$1("iron")[0],
		ironD: mat$1("iron")[1],
		wood: mat$1("wood")[0],
		woodD: mat$1("wood")[1],
		shaft: "#6a4420",
		grip: "#4a3020",
		brass: "#8a6a2a",
		gold: "#d8b04a",
		goldL: "#f6d878",
		leather: mat$1("leather")[0],
		leatherD: mat$1("leather")[1],
		skin: "#f1c9a5",
		cream: "#f2e6c8",
		arcane: "#9a86ff"
	};
	/** 元素色（照 `palette.ts`）：[主色, 亮色]。 */
	var EL = {
		fire: ["#ff6a1a", "#ffd23f"],
		ice: ["#8fe3ff", "#ffffff"],
		lightning: ["#fff36b", "#ffffff"],
		poison: ["#7ddc3a", "#d6f59a"],
		holy: ["#ffd75e", "#fff6c8"],
		shadow: ["#9a6ad8", "#d2b0ff"],
		wind: ["#7fe0c0", "#dcfff1"],
		earth: ["#b0814a", "#f0c890"],
		water: ["#4aa8ff", "#cfe8ff"]
	};
	var HI = "rgba(255,255,255,0.45)";
	var HI2 = "rgba(255,255,255,0.8)";
	var SH = "rgba(0,0,0,0.22)";
	var domCanvas = (w, h) => {
		if (typeof document === "undefined") return null;
		const cv = document.createElement("canvas");
		cv.width = w;
		cv.height = h;
		return cv;
	};
	var factory = domCanvas;
	/** 現在建得出畫布嗎（沒有 DOM、也沒有注入假畫布時不行）。 */
	var qCanvasAvailable = () => factory !== domCanvas || typeof document !== "undefined";
	/** 一張空白畫布（寬 w、高 h 裝置像素）。只在 `render` 裡用（`render` 先確認建得出畫布）。 */
	function blank(w, h = w) {
		const cv = factory(w, h);
		if (cv === null) throw new Error("qIcon: no canvas");
		return cv;
	}
	function ctxOf(cv) {
		const x = cv.getContext("2d");
		if (x === null) throw new Error("qIcon: no 2d context");
		return x;
	}
	var f = (c, col, path) => {
		c.beginPath();
		c.fillStyle = col;
		path(c);
		c.fill();
	};
	var rr = (c, col, x, y, w, h, r) => f(c, col, () => c.roundRect(x, y, w, h, r));
	var ci = (c, col, x, y, r) => f(c, col, () => c.arc(x, y, r, 0, TAU$3));
	var el = (c, col, x, y, rx, ry, rot = 0) => f(c, col, () => c.ellipse(x, y, rx, ry, rot, 0, TAU$3));
	/** 多邊形；round＞0 時用同色粗線把角磨圓（外形往外長 round 單位）。 */
	function poly(c, col, pts, round = 0) {
		c.beginPath();
		pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
		c.closePath();
		c.fillStyle = col;
		c.fill();
		if (round) {
			c.strokeStyle = col;
			c.lineWidth = round * 2;
			c.lineJoin = "round";
			c.stroke();
		}
	}
	function ln(c, col, w, pts, join = "round") {
		c.beginPath();
		pts.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = join === "round" ? "round" : "butt";
		c.lineJoin = join;
		c.miterLimit = 6;
		c.stroke();
	}
	function starPts(x, y, R, r, n, rot = -Math.PI / 2) {
		const p = [];
		for (let i = 0; i < n * 2; i++) {
			const a = rot + i * Math.PI / n, q = i % 2 ? r : R;
			p.push([x + Math.cos(a) * q, y + Math.sin(a) * q]);
		}
		return p;
	}
	/** 火焰外形：中心 (x,y)、高 20s、寬 14s，尖端朝上，左邊一小撮分岔。 */
	function flame$1(c, col, x, y, s) {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(.5, -10);
		c.bezierCurveTo(1.5, -5, 7, -3, 7, 3);
		c.bezierCurveTo(7, 7.5, 3.5, 10, 0, 10);
		c.bezierCurveTo(-3.5, 10, -7, 7.5, -7, 3);
		c.bezierCurveTo(-7, 0, -5, -2, -4.2, -4.8);
		c.bezierCurveTo(-3.5, -2.5, -2.6, -2, -1.8, -2.4);
		c.bezierCurveTo(-2.5, -5, -1.5, -8, .5, -10);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	}
	/** 剪影往一圈方向各位移 r（外圈）與 r/2（內圈）疊起來再染外框色（樣張 dilate；不用逐步膨脹，見樣張註解）。 */
	function dilate(src, r, col = OUT) {
		const w = src.width, h = src.height, o = blank(w, h), x = ctxOf(o), n = Math.max(16, Math.ceil(r * 5));
		for (const q of [1, .5]) for (let i = 0; i < n; i++) {
			const t = i / n * TAU$3;
			x.drawImage(src, Math.cos(t) * r * q, Math.sin(t) * r * q);
		}
		x.drawImage(src, 0, 0);
		x.globalCompositeOperation = "source-in";
		x.fillStyle = col;
		x.fillRect(0, 0, w, h);
		return o;
	}
	/** 圖樣裡前後重疊的零件：後畫的那一件自己先包一圈外框，兩件才分得開。 */
	function halo(c, o, fn, col = OUT, k = 1) {
		if (o.flat) {
			fn(c);
			return;
		}
		const cv = blank(c.canvas.width, c.canvas.height), x = ctxOf(cv);
		x.setTransform(c.getTransform());
		fn(x);
		c.save();
		c.setTransform(1, 0, 0, 1, 0, 0);
		if (o.owPx > 0) c.drawImage(dilate(cv, o.owPx * k, col), 0, 0);
		c.drawImage(cv, 0, 0);
		c.restore();
	}
	/** 外框粗細（CSS px）：顯示邊長的 5%，最細 1px、最粗 1.6px。 */
	var outlinePx = (px) => Math.min(1.6, Math.max(1, px * .05));
	/** 只畫圖樣（不含框）：回傳邊長 round(px×res) 的 canvas；建不出畫布時回傳 null。 */
	function render(def, px, res, opt = {}) {
		if (!qCanvasAvailable()) return null;
		const S = Math.max(4, Math.round(px * res)), o = {
			small: px <= 24,
			tiny: px <= 14,
			owPx: (opt.ow ?? outlinePx(px)) * res,
			badge: !!opt.badge,
			u: 48 / px
		};
		const main = blank(S), m = ctxOf(main);
		m.scale(S / 48, S / 48);
		def.d(m, o);
		const out = blank(S), x = ctxOf(out);
		if (def.pre) {
			x.save();
			x.scale(S / 48, S / 48);
			def.pre(x, o);
			x.restore();
		}
		if (o.owPx > 0) {
			const solid = blank(S), s = ctxOf(solid);
			s.scale(S / 48, S / 48);
			def.d(s, {
				...o,
				flat: true
			});
			x.drawImage(dilate(solid, o.owPx), 0, 0);
		}
		x.drawImage(main, 0, 0);
		if (def.post) {
			x.save();
			x.scale(S / 48, S / 48);
			def.post(x, o);
			x.restore();
		}
		return out;
	}
	/** 貼圖左上角（CSS px）：照 canvas 原尺寸、以 (x,y)～(x+a,y+a) 為中心、四捨五入到整數裝置像素（需求 3.1 第 1 點）。 */
	function blitOrigin(cvWidth, x, y, a, res) {
		const w = cvWidth / res, snap = (v) => Math.round(v * res) / res;
		return {
			x: snap(x + (a - w) / 2),
			y: snap(y + (a - w) / 2),
			w
		};
	}
	/** 把 `render` 畫好的圖樣貼上（不縮放、對齊整數裝置像素）。ctx 目前每單位 res 個裝置像素、原點在整數像素上。 */
	function blit(ctx, cv, x, y, a, res) {
		const p = blitOrigin(cv.width, x, y, a, res);
		ctx.drawImage(cv, p.x, p.y, p.w, p.w);
	}
	M.steel, M.steelD, M.brass, M.gold, M.wood, M.woodD, M.shaft, M.iron, M.ironD;
	mix("#6a4a2e", "#000000", .32);
	M.gold;
	M.goldL;
	var mat = (id) => MATERIAL[id] ?? MATERIAL["cloth"];
	mix(mat("cloth")[0], "#ffe6b8", .42);
	M.wood;
	Object.fromEntries(gearAppearance_default.kinds.map((k) => [k.id, k]));
	gearAppearance_default.maxKeywords;
	/** 造型清單（供預覽頁與測試用）。 */
	function gearKinds() {
		return gearAppearance_default.kinds;
	}
	new Set(gearKinds().filter((k) => k.paired).map((k) => k.id));
	MAT.gold;
	MAT.gold;
	MAT.wood;
	MAT.gold;
	MAT.wood;
	var POINT = {
		arm: -1.45,
		wpn: 3.02,
		lean: -.04
	};
	var AIM = {
		arm: -1.3,
		wpn: 2.87,
		lean: -.05
	};
	({ ...POINT }), { ...POINT }, { ...POINT }, { ...POINT }, { ...POINT }, { ...AIM }, { ...AIM }, { ...AIM }, { ...POINT };
	Object.freeze({
		kneeN: 1.4,
		kneeF: 1.2,
		hipN: .7,
		hipF: .5,
		bob: 7,
		lean: .25,
		arm: .3,
		armF: .35
	});
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/battle/vfxPalette.ts
	function vfx(primary, secondary, particle, particles = 10, extra = {}) {
		return {
			primary,
			secondary,
			particle,
			particles,
			jagged: false,
			column: false,
			...extra
		};
	}
	/** `#rrggbb` → 0xrrggbb。 */
	function hexToNumber(hex) {
		return parseInt(hex.slice(1), 16);
	}
	function fromColors(id, particle, particles, extra = {}) {
		const c = ELEMENT_COLORS[id];
		if (c === void 0) throw new Error(`ELEMENT_COLORS 缺少 ${id}`);
		return vfx(hexToNumber(c.primary), hexToNumber(c.secondary), particle, particles, extra);
	}
	fromColors("physical", "spark", 8), fromColors("fire", "ember", 12), fromColors("ice", "shard", 10), fromColors("lightning", "bolt", 7, { jagged: true }), fromColors("poison", "bubble", 9), fromColors("wind", "gust", 7), fromColors("earth", "rock", 9), fromColors("holy", "pillar", 9, { column: true }), fromColors("shadow", "smoke", 9), vfx(hexToNumber(WATER_COLOR), 14217471, "splash", 10);
	vfx(8188570, 15138793, "sparkle", 9);
	vfx(12101887, 16777215, "sparkle", 9);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/battle/vfx.ts
	/**
	* 技能卡 `shape` 文字的開頭（形狀的中文名，`skill_shapes.yaml` 的 `name_zh`）→ 形狀 id。
	* **只當最後的退回**：技能卡有 `icon`（Phase 3-17）時一律讀 `icon.segments[n].shape_id`；
	* 沒有 `icon` 的舊資料才用卡片的中文一句話（例如「錐形（大小 2）」「單體（射程 6）・穿透」）對照。
	*/
	var SHAPE_NAMES = {
		自身: "self",
		單體: "single",
		直線: "line",
		錐形: "cone",
		十字: "cross",
		方陣: "square3",
		環形: "ring",
		指定格: "ground_tile",
		連鎖: "chain",
		範圍光環: "allies_in_radius",
		物件與落點: "object_then_tile",
		單位與落點: "unit_then_tile",
		兩個單位: "unit_pair"
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/labels.ts
	/** 畫布文字的字型清單；須與 `styles/base.css` 的 `body` font-family 同步。 */
	var FONT = "'Noto Sans TC', 'Microsoft JhengHei', system-ui, sans-serif";
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/statusFrame.ts
	var isPolarity = (p) => p === "buff" || p === "debuff" || p === "neutral";
	/** 狀態的極性：沒有資料或不認得 → neutral。 */
	function polarityOf(id) {
		const p = id == null ? void 0 : statusLook(id)?.polarity;
		return isPolarity(p) ? p : "neutral";
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/qIcon/legacy48.ts
	/** 水滴外形：中心 (x,y)、高 20s、寬 14s，尖端朝上（樣張 H.drop）。 */
	function drop$2(c, col, x, y, s) {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(0, -10);
		c.bezierCurveTo(4, -4, 7, 0, 7, 4);
		c.bezierCurveTo(7, 8, 3.5, 10, 0, 10);
		c.bezierCurveTo(-3.5, 10, -7, 8, -7, 4);
		c.bezierCurveTo(-7, 0, -4, -4, 0, -10);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	}
	/** 一根插在土堆上的木雕圖騰柱：頂上一對紅翅、兩張臉（樣張 SKILL_V1.skill_plant_totem.d）。 */
	function totemPole(c, o) {
		el(c, "#6a4a2e", 24, 41.5, 14.5, 3.6);
		poly(c, "#c0392b", [
			[17, 9],
			[5, 6],
			[8, 11.5],
			[4.5, 13],
			[9.5, 15],
			[17, 15.5]
		], .5);
		poly(c, "#c0392b", [
			[31, 9],
			[43, 6],
			[40, 11.5],
			[43.5, 13],
			[38.5, 15],
			[31, 15.5]
		], .5);
		rr(c, M.wood, 16.5, 5, 15, 36.5, 3.4);
		f(c, "#b98048", () => c.roundRect(16.5, 5, 4.4, 36.5, [
			3.4,
			0,
			0,
			3.4
		]));
		f(c, M.woodD, () => c.rect(16.5, 21.4, 15, 1.7));
		for (const y of [11, 28]) {
			rr(c, "#fff6c8", 19, y, 3.6, 3.6, .8);
			rr(c, "#fff6c8", 25.4, y, 3.6, 3.6, .8);
			if (!o.small) {
				f(c, OUT, () => c.rect(20.3, y + 1, 1.5, 1.8));
				f(c, OUT, () => c.rect(26.7, y + 1, 1.5, 1.8));
			}
		}
		rr(c, M.woodD, 20.6, 16.6, 6.8, 2.4, 1);
		poly(c, "#e8bb48", [
			[20, 34.5],
			[22, 37.5],
			[24, 34.5],
			[26, 37.5],
			[28, 34.5],
			[28, 36],
			[26, 39],
			[24, 36],
			[22, 39],
			[20, 36]
		]);
	}
	/** 樣張 `QIcons.ART` 裡第 4 批用到的兩類（只搬用到的款）。 */
	var ART = {
		status: {
			prone: {
				zh: "倒地",
				d: (c, o) => {
					const k = "#f2e6c8";
					if (o.tiny) {
						rr(c, "#a89878", 1.5, 39.5, 45, 5.5, 2);
						rr(c, k, 17, 19.5, 29.5, 15.5, 6.5);
						ci(c, k, 12.5, 25, 11.5);
						f(c, "#ffffff", () => c.ellipse(9, 20.6, 4, 2.8, -.5, 0, TAU$3));
						return;
					}
					halo(c, o, (x) => {
						poly(x, "#ffd23f", starPts(24, 11, 10.5, 4.8, 7, -1.2), .5);
						poly(x, "#ffffff", starPts(24, 11, 4.8, 2.3, 7, -1.2));
					});
					rr(c, "#8a7a6a", 2.5, 40.8, 43, 4, 2);
					halo(c, o, (x) => {
						ln(x, k, 6, [[30, 36.2], [43, 36.6]]);
						ln(x, k, 6, [[30, 33], [39.5, 25.5]]);
						rr(x, k, 17, 28.4, 16.5, 11.2, 5);
						ci(x, k, 11.5, 29.6, 9.6);
						f(x, "#ffffff", () => x.ellipse(8.6, 26, 3.2, 2.2, -.5, 0, TAU$3));
						f(x, "rgba(120,90,50,0.3)", () => x.rect(19, 37, 13, 2.6));
					});
				}
			},
			frozen: {
				zh: "冰凍",
				d: (c, o) => {
					poly(c, "#8fe3ff", [
						[12, 17],
						[17.5, 25],
						[16.5, 42],
						[7, 42],
						[6, 26]
					], .8);
					poly(c, "#8fe3ff", [
						[36.5, 20],
						[42, 28],
						[41, 42],
						[32, 42],
						[31, 28]
					], .8);
					poly(c, "#b8efff", [
						[24, 4.5],
						[31.5, 17],
						[29.5, 42],
						[18.5, 42],
						[16.5, 17]
					], .8);
					poly(c, "#ffffff", [
						[24, 7],
						[24, 40.5],
						[19.6, 40.5],
						[18, 17.4]
					]);
					if (!o.tiny) {
						poly(c, "#3fa6d8", [
							[29.2, 20],
							[30.4, 17.6],
							[28.6, 41],
							[26.4, 41]
						]);
						poly(c, "#e8fbff", [
							[11.6, 20],
							[11.6, 41],
							[8.4, 41],
							[7.6, 26.4]
						]);
						poly(c, "#e8fbff", [
							[36, 23],
							[36, 41],
							[33.2, 41],
							[32.6, 28.4]
						]);
					}
				}
			},
			hasted: {
				zh: "加速",
				d: (c, o) => {
					if (o.tiny) {
						for (const dx of [.5, 23.5]) {
							poly(c, "#7dffb0", [
								[dx, 6],
								[dx + 11, 6],
								[dx + 23, 24],
								[dx + 11, 42],
								[dx, 42],
								[dx + 12, 24]
							]);
							poly(c, "#e2fff0", [
								[dx, 6],
								[dx + 11, 6],
								[dx + 23, 24],
								[dx + 12, 24]
							]);
						}
						return;
					}
					for (const dx of [3, 20]) {
						poly(c, "#7dffb0", [
							[dx, 9],
							[dx + 10, 9],
							[dx + 22, 24],
							[dx + 10, 39],
							[dx, 39],
							[dx + 12, 24]
						], .9);
						poly(c, "#d6ffe6", [
							[dx + 1, 10],
							[dx + 9.6, 10],
							[dx + 20.6, 24],
							[dx + 12, 24]
						]);
					}
				}
			},
			feared: {
				zh: "恐懼",
				d: (c, o) => {
					f(c, "#ece4ff", () => {
						c.moveTo(6, 43);
						c.lineTo(6, 23);
						c.bezierCurveTo(6, 0, 42, 0, 42, 23);
						c.lineTo(42, 43);
						c.lineTo(36, 37.5);
						c.lineTo(30, 43);
						c.lineTo(24, 37.5);
						c.lineTo(18, 43);
						c.lineTo(12, 37.5);
						c.closePath();
					});
					if (!o.tiny) f(c, "rgba(120,90,200,0.3)", () => {
						c.moveTo(33, 7.5);
						c.bezierCurveTo(40, 12, 42, 18, 42, 23);
						c.lineTo(42, 43);
						c.lineTo(36.4, 37.8);
						c.lineTo(36.4, 22);
						c.bezierCurveTo(36.4, 16, 35.4, 11, 33, 7.5);
						c.closePath();
					});
					el(c, OUT, 17.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8);
					el(c, OUT, 30.5, 21, o.tiny ? 4 : 3.3, o.tiny ? 5.6 : 4.8);
					if (!o.tiny) el(c, OUT, 24, 31, 3.2, 2.6);
				}
			}
		},
		hud: {
			ap: {
				zh: "AP（行動點）",
				d: (c, o) => {
					poly(c, "#ffd23a", [
						[27, 3.5],
						[9.5, 27],
						[21, 27],
						[16, 44.5],
						[38.5, 19.5],
						[27, 19.5],
						[33.5, 3.5]
					], 1);
					if (!o.tiny) poly(c, "#fff3a0", [
						[27.4, 5],
						[12.6, 25.6],
						[17, 25.6],
						[31, 5]
					]);
				}
			},
			mana: {
				zh: "法力",
				d: (c, _o) => {
					drop$2(c, "#4a8ae0", 24, 24.5, 2.1);
					c.save();
					c.beginPath();
					c.rect(0, 0, 48, 48);
					c.clip();
					f(c, "rgba(20,40,110,0.38)", () => {
						c.moveTo(24, 45.5);
						c.bezierCurveTo(34, 45.5, 40, 38, 38.4, 29.5);
						c.bezierCurveTo(37, 37, 31, 41, 24, 41.5);
						c.closePath();
					});
					c.restore();
					el(c, "#cfe4ff", 18, 28.5, 2.6, 5.6, .45);
				}
			},
			stamina: {
				zh: "耐力",
				d: (c, o) => {
					const P = [
						[4.5, 26],
						[13.5, 26],
						[19, 11.5],
						[27.5, 37.5],
						[32.5, 24],
						[43.5, 24]
					];
					ln(c, "#e8bb48", 6.4, P);
					if (!o.tiny) ln(c, "#fff0b0", 1.6, P.map(([x, y]) => [x - .6, y - 1.2]));
				}
			},
			move: {
				zh: "移動",
				d: (c, o) => {
					rr(c, "#a07040", 12.5, 5.5, 15.5, 30, 4);
					f(c, "#a07040", () => {
						c.moveTo(12.5, 24);
						c.lineTo(27, 24);
						c.quadraticCurveTo(41.5, 25.5, 42.5, 35.5);
						c.lineTo(42.5, 39);
						c.lineTo(12.5, 39);
						c.closePath();
					});
					rr(c, "#5e3b1f", 11, 38, 33, 5.4, 2.2);
					rr(c, "#e0c088", 11, 4.5, 18.5, 7.6, 3.2);
					if (!o.tiny) {
						f(c, HI, () => c.rect(15, 13.5, 2.2, 20));
						f(c, "rgba(0,0,0,0.2)", () => {
							c.moveTo(28, 26);
							c.quadraticCurveTo(39.5, 27.5, 41, 36);
							c.lineTo(28, 36);
							c.closePath();
						});
					}
				}
			}
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/skillGlyphs.ts
	var TAU$2 = Math.PI * 2;
	Object.fromEntries(Object.entries(ELEMENT_COLORS).map(([id, c]) => [id, {
		name: c.name,
		accent: c.accent,
		dark: c.dark,
		light: c.light
	}]));
	function starPath(ctx, cx, cy, n, ro, ri, rot = -Math.PI / 2) {
		ctx.beginPath();
		for (let i = 0; i < n * 2; i++) {
			const r = i % 2 === 0 ? ro : ri;
			const a = rot + i / (n * 2) * TAU$2;
			ctx.lineTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
		}
		ctx.closePath();
	}
	function elementGlyph(ctx, el, cx, cy, k, color) {
		ctx.save();
		ctx.translate(cx, cy);
		ctx.scale(k, k);
		ctx.fillStyle = color;
		ctx.strokeStyle = color;
		ctx.lineCap = "round";
		ctx.lineJoin = "round";
		switch (el) {
			case "fire":
				ctx.beginPath();
				ctx.moveTo(0, -10);
				ctx.bezierCurveTo(7, -3, 8, 3, 0, 9);
				ctx.bezierCurveTo(-8, 3, -6, -2, -2, -4);
				ctx.bezierCurveTo(-2, -1, 0, 0, 0, -10);
				ctx.fill();
				break;
			case "ice":
				iceGlyph(ctx);
				break;
			case "lightning":
				ctx.beginPath();
				ctx.moveTo(3, -11);
				ctx.lineTo(-6, 1);
				ctx.lineTo(0, 1);
				ctx.lineTo(-3, 11);
				ctx.lineTo(7, -2);
				ctx.lineTo(1, -2);
				ctx.lineTo(5, -11);
				ctx.closePath();
				ctx.fill();
				break;
			case "poison":
				ctx.beginPath();
				ctx.moveTo(0, -10);
				ctx.bezierCurveTo(8, -1, 8, 8, 0, 8);
				ctx.bezierCurveTo(-8, 8, -8, -1, 0, -10);
				ctx.fill();
				ctx.fillStyle = "rgba(0,0,0,0.35)";
				ctx.beginPath();
				ctx.arc(-2, 2, 2.2, 0, TAU$2);
				ctx.arc(2.5, 4.5, 1.4, 0, TAU$2);
				ctx.fill();
				break;
			case "wind":
				ctx.lineWidth = 2.6;
				ctx.beginPath();
				ctx.moveTo(-10, -4);
				ctx.lineTo(4, -4);
				ctx.arc(4, -7.5, 3.5, Math.PI / 2, -Math.PI * .9, true);
				ctx.moveTo(-10, 2);
				ctx.lineTo(7, 2);
				ctx.arc(7, 6, 4, -Math.PI / 2, Math.PI * .9);
				ctx.moveTo(-7, 8);
				ctx.lineTo(-1, 8);
				ctx.stroke();
				break;
			case "earth":
				ctx.beginPath();
				ctx.moveTo(-11, 8);
				ctx.lineTo(-4, -6);
				ctx.lineTo(0, 0);
				ctx.lineTo(4, -9);
				ctx.lineTo(11, 8);
				ctx.closePath();
				ctx.fill();
				break;
			case "holy":
				starPath(ctx, 0, 0, 4, 11, 3.2);
				ctx.fill();
				starPath(ctx, 0, 0, 4, 6, 2, -Math.PI / 4);
				ctx.fill();
				break;
			case "shadow":
				ctx.beginPath();
				ctx.arc(0, 0, 9, 0, TAU$2);
				ctx.arc(4, -3, 7.5, 0, TAU$2, true);
				ctx.fill("evenodd");
				break;
			case "physical":
				starPath(ctx, 0, 0, 4, 10, 2.6, 0);
				ctx.fill();
				break;
			default:
				ctx.beginPath();
				for (let i = 0; i < 6; i++) ctx.lineTo(Math.cos(i / 6 * TAU$2) * 8, Math.sin(i / 6 * TAU$2) * 8);
				ctx.closePath();
				ctx.fill();
				ctx.fillStyle = "rgba(255,255,255,0.6)";
				ctx.fillRect(-2, -5, 3, 10);
		}
		ctx.restore();
	}
	function iceGlyph(ctx) {
		ctx.lineWidth = 2.4;
		ctx.beginPath();
		for (let i = 0; i < 3; i++) {
			const a = i / 3 * Math.PI + Math.PI / 2;
			ctx.moveTo(Math.cos(a) * 9, Math.sin(a) * 9);
			ctx.lineTo(-Math.cos(a) * 9, -Math.sin(a) * 9);
		}
		for (let i = 0; i < 6; i++) {
			const a = i / 6 * TAU$2 + Math.PI / 2;
			const bx = Math.cos(a) * 5.5;
			const by = Math.sin(a) * 5.5;
			ctx.moveTo(bx, by);
			ctx.lineTo(bx + Math.cos(a + .8) * 3.5, by + Math.sin(a + .8) * 3.5);
			ctx.moveTo(bx, by);
			ctx.lineTo(bx + Math.cos(a - .8) * 3.5, by + Math.sin(a - .8) * 3.5);
		}
		ctx.stroke();
	}
	Array.from({ length: 25 }, (_, i) => i % 5 === 2 || Math.floor(i / 5) === 2 ? 1 : 0);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/qIcon/skills.ts
	/** 有固定鍵的表：點名取值不會是 undefined；用字串查時可能是 undefined（樣張一律接 `??` 退回）。 */
	var table = () => (o) => o;
	var st$2 = (c, col, w, fn, cap = "round") => {
		c.beginPath();
		fn(c);
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = cap;
		c.lineJoin = "round";
		c.stroke();
	};
	var at$2 = (c, x, y, k, fn, rot = 0) => {
		c.save();
		c.translate(x, y);
		c.rotate(rot);
		c.scale(k, k);
		fn(c);
		c.restore();
	};
	/** 把畫在 48 格（中心 24,24）的東西縮放後放到 (x,y)。 */
	var place = (c, x, y, k, fn) => {
		c.save();
		c.translate(x, y);
		c.scale(k, k);
		c.translate(-24, -24);
		fn(c);
		c.restore();
	};
	var rgba = (hex, a) => {
		const p = [
			1,
			3,
			5
		].map((i) => parseInt(hex.slice(i, i + 2), 16));
		return `rgba(${p[0]},${p[1]},${p[2]},${a})`;
	};
	table()({
		physical: [
			"#2c313b",
			"#7d8798",
			"#e8ebf0"
		],
		fire: [
			"#4a1104",
			"#e8541a",
			"#ffb23a"
		],
		ice: [
			"#0b2f4e",
			"#3fa6d8",
			"#d8f6ff"
		],
		lightning: [
			"#1d1d4a",
			"#5a5ac8",
			"#fff36b"
		],
		poison: [
			"#12320c",
			"#4f9a28",
			"#b6f06a"
		],
		wind: [
			"#0b3f3a",
			"#3fb59a",
			"#dcfff1"
		],
		earth: [
			"#2e1d0e",
			"#9a6a36",
			"#f0c890"
		],
		holy: [
			"#5a3a06",
			"#e7b23a",
			"#fff6c8"
		],
		shadow: [
			"#10071e",
			"#5a3590",
			"#d2b0ff"
		],
		default: [
			"#221c44",
			"#6a5ad0",
			"#e8e0ff"
		]
	});
	var BASE_ZH = {
		physical: "物理",
		fire: "火",
		ice: "冰",
		lightning: "雷",
		poison: "毒",
		wind: "風",
		earth: "大地",
		holy: "聖光",
		shadow: "暗影",
		default: "（無）"
	};
	table()({
		common: "#9aa0a6",
		rare: "#4da3ff",
		epic: "#b06cff",
		legendary: "#ffbf3a"
	});
	/** 染色：元素色照 qIcons.js 的 EL；另外三個不是元素的——血（流血、標記、易傷）、鋼（守護、煙）、撞擊（倒地、碰撞）。 */
	var TINT = table()({
		...EL,
		arcane: ["#b8a8ff", "#ece6ff"],
		blood: ["#e8455a", "#ffb0b8"],
		steel: ["#c3ccd6", "#ffffff"],
		impact: ["#ffd23f", "#ffffff"],
		stone: ["#b4ac9a", "#ece6d6"]
	});
	var ELEMENT$1 = table()({
		fire: {
			zh: "火焰",
			d: (c) => {
				flame$1(c, "#ff6a1a", 24, 24, 1.55);
				flame$1(c, "#ffd23f", 24.5, 28, .98);
				el(c, "#ffffff", 24.6, 32, 2.5, 4.2);
			}
		},
		ice: {
			zh: "冰晶",
			d: (c, o) => {
				poly(c, "#6fc8ee", [
					[12.5, 17],
					[18, 22],
					[19.5, 39],
					[10.5, 39],
					[8, 25]
				], .6);
				poly(c, "#6fc8ee", [
					[35.5, 19],
					[40, 27],
					[37.5, 39],
					[28.5, 39],
					[30, 24]
				], .6);
				poly(c, "#8fe3ff", [
					[24, 5],
					[31, 14.5],
					[29, 39.5],
					[19, 39.5],
					[17, 14.5]
				], .6);
				poly(c, "#ffffff", [
					[24, 5],
					[17, 14.5],
					[19, 39.5],
					[22.4, 39.5],
					[22.4, 12]
				]);
				poly(c, "#4aa8d8", [
					[27.6, 12],
					[31, 14.5],
					[29, 39.5],
					[27.6, 39.5]
				]);
				if (!o.small) {
					poly(c, "#e6faff", [
						[12.5, 17],
						[8, 25],
						[10.5, 39],
						[12.6, 39]
					]);
					poly(c, "#e6faff", [
						[35.5, 19],
						[30, 24],
						[28.5, 39],
						[31, 39]
					]);
				}
			}
		},
		lightning: {
			zh: "閃電",
			d: (c) => {
				poly(c, "#fff36b", [
					[29, 4],
					[11, 26.5],
					[21, 26.5],
					[16, 44],
					[37, 19.5],
					[26.5, 19.5],
					[32.5, 4]
				], .7);
				poly(c, "#ffb400", [
					[21, 26.5],
					[16, 44],
					[37, 19.5],
					[31.5, 19.5],
					[22.6, 31.5],
					[24.5, 26.5]
				]);
				poly(c, "#ffffff", [
					[28.6, 8],
					[16.5, 23.6],
					[22.4, 23.6],
					[29.6, 8]
				]);
			}
		},
		poison: {
			zh: "毒液",
			d: (c, o) => {
				drop$2(c, "#7ddc3a", 22.5, 26, 1.58);
				drop$2(c, "#b6f06a", 21.6, 28, 1.02);
				el(c, "#f2ffd8", 18, 28.5, 1.9, 4.2, .4);
				ci(c, "#7ddc3a", 36, 12, 4.2);
				ci(c, "#d6f59a", 35, 11, 1.7);
				if (!o.small) {
					ci(c, "#7ddc3a", 39.5, 22.5, 2.6);
					ci(c, "#3f8a1e", 20, 33.5, 1.5);
					ci(c, "#3f8a1e", 26, 30, 1.2);
				}
			}
		},
		wind: {
			zh: "旋風",
			d: (c, o) => {
				const curl = (x) => {
					x.moveTo(6.5, 29);
					x.bezierCurveTo(6, 11, 33, 6, 37, 18.5);
					x.bezierCurveTo(39.4, 27.5, 26.5, 31.5, 23.4, 24.2);
					x.bezierCurveTo(22, 20, 27, 17.6, 29.4, 20.4);
				};
				st$2(c, "#7fe0c0", 7, curl);
				st$2(c, "#7fe0c0", 5.6, (x) => {
					x.moveTo(11, 39.5);
					x.quadraticCurveTo(28, 44, 41, 33.5);
				});
				st$2(c, "#ffffff", 2, (x) => {
					x.moveTo(8.2, 24);
					x.bezierCurveTo(10, 13.5, 24, 9.5, 31.5, 13);
				});
				if (!o.small) st$2(c, "#dcfff1", 1.5, (x) => {
					x.moveTo(14, 38.6);
					x.quadraticCurveTo(26, 41.4, 35, 36.4);
				});
			}
		},
		earth: {
			zh: "岩石",
			d: (c, o) => {
				poly(c, "#b0814a", [
					[8.5, 34],
					[12, 17.5],
					[22.5, 8.5],
					[35.5, 12],
					[40.5, 26.5],
					[35.5, 38.5],
					[14, 39.5]
				], 1.4);
				poly(c, "#dab07a", [
					[12, 17.5],
					[22.5, 8.5],
					[35.5, 12],
					[25, 21.5]
				], .6);
				poly(c, "#7e5a30", [
					[25, 21.5],
					[35.5, 12],
					[40.5, 26.5],
					[35.5, 38.5],
					[27, 39.5]
				], .6);
				if (!o.small) {
					ln(c, "#5a3d1c", 1.4, [
						[25, 21.5],
						[20.5, 29],
						[23, 34]
					]);
					poly(c, "#f6dcb0", [
						[14.5, 19],
						[21.5, 12.6],
						[22.6, 14.4],
						[16, 20.6]
					]);
				}
			}
		},
		holy: {
			zh: "聖光",
			d: (c, _o) => {
				poly(c, "#e7a020", starPts(24, 24, 12.5, 6, 4, Math.PI / 4), .6);
				poly(c, "#ffd75e", starPts(24, 24, 20.5, 6.4, 4), .8);
				poly(c, "#fff6c8", starPts(24, 24, 12.5, 4, 4));
				ci(c, "#ffffff", 24, 24, 4.6);
			}
		},
		shadow: {
			zh: "暗月",
			d: (c, o) => {
				const moon = (x, R, r) => {
					x.arc(24, 24, R, .2417, 4.652, false);
					x.arc(30, 19, r, -2.137, .747, true);
					x.closePath();
				};
				f(c, "#b48aee", () => moon(c, 17, 13.8));
				c.save();
				c.beginPath();
				moon(c, 17, 13.8);
				c.clip();
				f(c, "#e6d2ff", () => c.ellipse(15, 22, 5.5, 13, .25, 0, TAU$3));
				f(c, "#7a4ec0", () => c.ellipse(27, 38, 13, 5, -.5, 0, TAU$3));
				c.restore();
				poly(c, "#e6d2ff", starPts(33.5, 16.5, 6.6, 2.5, 4), .3);
				if (!o.small) poly(c, "#ffffff", starPts(33.5, 16.5, 3, 1.2, 4));
			}
		},
		water: {
			zh: "水滴與波紋",
			d: (c, _o) => {
				const wave = (y, w) => st$2(c, "#4aa8ff", w, (x) => {
					x.moveTo(6.5, y);
					x.bezierCurveTo(12, y - 6.5, 18, y - 6.5, 24, y);
					x.bezierCurveTo(30, y + 6.5, 36, y + 6.5, 41.5, y);
				});
				wave(39, 6.4);
				wave(30.5, 6.8);
				st$2(c, "#cfe8ff", 1.8, (x) => {
					x.moveTo(8.5, 29);
					x.bezierCurveTo(12.5, 24.6, 17.5, 24.6, 22.5, 28.6);
				});
				drop$2(c, "#4aa8ff", 24, 14.5, 1.12);
				drop$2(c, "#8fd0ff", 23.4, 16, .7);
				el(c, "#ffffff", 21, 16.5, 1.4, 3, .4);
			}
		},
		arcane: {
			zh: "奧術晶石",
			d: (c, _o) => {
				poly(c, "#b8a8ff", [
					[24, 5.5],
					[36.5, 15],
					[36.5, 31],
					[24, 42.5],
					[11.5, 31],
					[11.5, 15]
				], .9);
				poly(c, "#ece6ff", [
					[24, 5.5],
					[11.5, 15],
					[24, 20.5]
				]);
				poly(c, "#d2c8ff", [
					[11.5, 15],
					[11.5, 31],
					[24, 20.5]
				]);
				poly(c, "#7a68c8", [
					[36.5, 15],
					[36.5, 31],
					[24, 42.5],
					[24, 20.5]
				]);
				poly(c, "#9a86ff", [
					[11.5, 31],
					[24, 42.5],
					[24, 20.5]
				]);
				poly(c, "#ffffff", starPts(24, 21, 5.6, 1.9, 4));
			}
		}
	});
	var eyes = (c, x1, x2, y, rx, ry, col = OUT) => {
		el(c, col, x1, y, rx, ry);
		el(c, col, x2, y, rx, ry);
	};
	function spiritArt(c, o, T) {
		const body = (x) => {
			x.moveTo(24, 5.5);
			x.bezierCurveTo(35.5, 5.5, 39.5, 17, 36.5, 26);
			x.bezierCurveTo(34.5, 32.5, 37.5, 37, 42, 38.6);
			x.bezierCurveTo(33.5, 43.6, 23, 42.5, 16.5, 37.6);
			x.bezierCurveTo(7.5, 31, 7.5, 18.5, 13.5, 11.5);
			x.bezierCurveTo(16.5, 7.6, 20, 5.5, 24, 5.5);
			x.closePath();
		};
		f(c, T[0], () => body(c));
		c.save();
		c.beginPath();
		body(c);
		c.clip();
		f(c, T[1], () => c.ellipse(21, 17, 9.5, 8.6, -.3, 0, TAU$3));
		f(c, SH, () => c.ellipse(34, 36, 13, 6, .5, 0, TAU$3));
		c.restore();
		eyes(c, 19.5, 28, 20, 2.3, 3.3);
		if (!o.small) {
			ci(c, "#ffffff", 20.2, 18.8, .8);
			ci(c, "#ffffff", 28.7, 18.8, .8);
			st$2(c, OUT, 1.3, (x) => {
				x.moveTo(21.6, 26.4);
				x.quadraticCurveTo(24, 28.4, 26.4, 26.4);
			});
		}
	}
	function shadeArt(c, o, body, hood, eye) {
		const P = (x) => {
			x.moveTo(24, 4.5);
			x.bezierCurveTo(35.5, 4.5, 38.5, 15, 38.5, 25);
			x.lineTo(38.5, 42);
			x.lineTo(33.7, 37);
			x.lineTo(28.8, 42);
			x.lineTo(24, 37);
			x.lineTo(19.2, 42);
			x.lineTo(14.3, 37);
			x.lineTo(9.5, 42);
			x.lineTo(9.5, 25);
			x.bezierCurveTo(9.5, 15, 12.5, 4.5, 24, 4.5);
			x.closePath();
		};
		f(c, body, () => P(c));
		c.save();
		c.beginPath();
		P(c);
		c.clip();
		f(c, mix(body, "#ffffff", .4), () => c.rect(9, 4, 6.5, 40));
		f(c, SH, () => c.rect(32.5, 4, 7, 40));
		c.restore();
		el(c, hood, 24, 19.5, 9.6, 8.6);
		eyes(c, 20, 28, 19.5, 2.4, 3, eye);
		if (!o.small) eyes(c, 20, 28, 19.5, 1, 1.5, "#ffffff");
	}
	table()({
		spirit: {
			zh: "靈（元素之靈、火靈、冰靈、雷靈、水精）",
			d: (c, o, T) => spiritArt(c, o, T ?? TINT.arcane)
		},
		guardian: {
			zh: "守護靈",
			d: (c, o) => {
				for (const s of [-1, 1]) poly(c, "#fff6c8", [
					[24 + s * 9, 17],
					[24 + s * 21.5, 10],
					[24 + s * 20, 20],
					[24 + s * 22, 26],
					[24 + s * 15, 27.5],
					[24 + s * 9, 30]
				], .8);
				place(c, 24, 26.5, .8, (x) => spiritArt(x, o, ["#ffd75e", "#fff6c8"]));
				if (o.small) st$2(c, "#ffd23f", 3.2, (x) => x.ellipse(24, 7.7, 9.6, 3.4, 0, 0, TAU$3));
				else st$2(c, "#ffe9a8", 2.6, (x) => x.ellipse(24, 6.6, 8, 2.6, 0, 0, TAU$3));
			}
		},
		skeleton: {
			zh: "骷髏戰士",
			d: (c, o) => {
				rr(c, "#cfc8b0", 16.5, 27, 15, 12.5, 3.4);
				ci(c, "#e9e3cf", 24, 19.5, 14);
				f(c, HI2, () => c.ellipse(18, 12.5, 5, 3, -.5, 0, TAU$3));
				f(c, SH, () => {
					c.arc(24, 19.5, 14, -.9, 1.3);
					c.closePath();
				});
				eyes(c, 18.6, 29.4, 21, 3.6, 4.4, "#2a2230");
				poly(c, "#2a2230", [
					[24, 25],
					[26, 29.4],
					[22, 29.4]
				]);
				if (!o.small) for (const x of [
					20.4,
					24,
					27.6
				]) f(c, "#2a2230", () => c.rect(x - .5, 33, 1, 6));
				else f(c, "#2a2230", () => c.rect(18.6, 34.4, 10.8, 1.6));
			}
		},
		shade: {
			zh: "影魅、霧影",
			d: (c, o, T) => T && T[0] === TINT.ice[0] ? shadeArt(c, o, "#a8cfe6", "#2c4a66", "#f2fbff") : shadeArt(c, o, "#9a6ad8", "#2a1650", "#f0e0ff")
		},
		golem: {
			zh: "石像",
			d: (c, o) => {
				ci(c, "#8c8474", 9.5, 28, 6.5);
				ci(c, "#8c8474", 38.5, 28, 6.5);
				rr(c, "#9a9282", 10, 22.5, 28, 19, 5.5);
				rr(c, "#b4ac9a", 13, 6, 22, 19, 4.5);
				f(c, "#d6cfbe", () => c.roundRect(13, 6, 6, 19, [
					4.5,
					0,
					0,
					4.5
				]));
				f(c, SH, () => c.roundRect(30, 6, 5, 19, [
					0,
					4.5,
					4.5,
					0
				]));
				f(c, "#6e6656", () => c.rect(13, 11.5, 22, 3));
				rr(c, "#8ff0e2", 16.6, 15.6, 4.6, 4, 1);
				rr(c, "#8ff0e2", 26.8, 15.6, 4.6, 4, 1);
				if (!o.small) {
					ln(c, "#6e6656", 1.3, [
						[24, 26],
						[21.5, 31],
						[25, 35]
					]);
					f(c, "#c8c0ae", () => c.rect(12.5, 25, 5, 2));
				}
			}
		},
		bomb: {
			zh: "爆裂傀儡",
			d: (c, o) => {
				st$2(c, "#a06a36", 3, (x) => {
					x.moveTo(29, 15.5);
					x.quadraticCurveTo(31, 8.5, 37, 8);
				});
				poly(c, "#ffd23f", starPts(38.5, 7.5, 6, 2.6, 6), .3);
				ci(c, "#ffffff", 38.5, 7.5, 1.9);
				rr(c, "#8a8f99", 22.5, 11.5, 9, 6, 1.6);
				ci(c, "#c8553a", 22.5, 28, 14.5);
				f(c, "#e8826a", () => c.ellipse(16.5, 20.5, 6, 4, -.6, 0, TAU$3));
				f(c, SH, () => {
					c.arc(22.5, 28, 14.5, -.3, 1.9);
					c.closePath();
				});
				poly(c, "#fff6c8", [
					[14, 24.6],
					[21, 27],
					[20.4, 31.4],
					[14.6, 30.4]
				], .4);
				poly(c, "#fff6c8", [
					[31, 24.6],
					[24, 27],
					[24.6, 31.4],
					[30.4, 30.4]
				], .4);
				if (!o.small) ln(c, "#2a1c14", 1.5, [
					[16.5, 36],
					[19.5, 34],
					[22.5, 36],
					[25.5, 34],
					[28.5, 36]
				], "miter");
			}
		},
		wall: {
			zh: "土牆",
			d: (c, _o) => {
				for (const [x, y, w] of [
					[
						5,
						29.5,
						18.5
					],
					[
						24.5,
						29.5,
						18.5
					],
					[
						5,
						18,
						11.5
					],
					[
						17.5,
						18,
						17.5
					],
					[
						36,
						18,
						7
					],
					[
						9,
						6.5,
						14
					],
					[
						24,
						6.5,
						15
					]
				]) {
					rr(c, "#b0814a", x, y, w, 10.5, 2.2);
					f(c, "#dab07a", () => c.roundRect(x, y, w, 3.4, [
						2.2,
						2.2,
						0,
						0
					]));
					f(c, "#7e5a30", () => c.roundRect(x, y + 8, w, 2.5, [
						0,
						0,
						2.2,
						2.2
					]));
				}
				rr(c, "#7ab04a", 8, 4.6, 31.5, 3.6, 1.8);
			}
		},
		wolf: {
			zh: "戰狼",
			d: (c, o) => wolfHead(c, o, "#9aa3ad", "#6a737d", "#e6ebf0", "#ffd23f", false)
		},
		hawk: {
			zh: "鷹隼",
			d: (c, o) => {
				for (const s of [-1, 1]) {
					poly(c, "#a06a36", [
						[24 + s * 3, 18],
						[24 + s * 20.5, 7.5],
						[24 + s * 19, 17],
						[24 + s * 21.5, 20.5],
						[24 + s * 16.5, 26],
						[24 + s * 4, 29]
					], .8);
					poly(c, "#d8b078", [
						[24 + s * 4, 19.6],
						[24 + s * 18, 11],
						[24 + s * 16, 15.6],
						[24 + s * 5, 23]
					]);
				}
				poly(c, "#7e5a30", [
					[19.5, 30],
					[28.5, 30],
					[31.5, 41],
					[24, 37.5],
					[16.5, 41]
				], .7);
				el(c, "#a06a36", 24, 25, 5.6, 9.6);
				ci(c, "#f2ead8", 24, 14.5, 5.4);
				poly(c, "#f0b030", [
					[21.6, 16.5],
					[26.4, 16.5],
					[24, 22]
				], .3);
				if (!o.small) eyes(c, 21.8, 26.2, 13.6, .9, 1.1);
			}
		},
		whelp: {
			zh: "餘燼幼蜥",
			d: (c, o) => {
				const B = o.small ? "#ffb44e" : "#ff8a3a", sp = o.small ? "#fff3a8" : "#ffe14d";
				st$2(c, B, 4.4, (x) => {
					x.moveTo(15.5, 34);
					x.quadraticCurveTo(12.5, 42.5, 8.5, 36.5);
				});
				flame$1(c, "#ff6a1a", 8.6, 28.6, .66);
				flame$1(c, "#ffd23f", 8.8, 30.2, .38);
				for (const [x0, y0, x1, y1] of [
					[
						18.5,
						22.5,
						11.5,
						19
					],
					[
						26,
						31,
						29.5,
						38.5
					],
					[
						28.5,
						17.5,
						22.5,
						11.5
					],
					[
						31,
						24,
						38,
						27.5
					]
				]) st$2(c, "#e86a1a", 3.6, (x) => {
					x.moveTo(x0, y0);
					x.lineTo(x1, y1);
				});
				st$2(c, B, 9.5, (x) => {
					x.moveTo(15.5, 35);
					x.bezierCurveTo(18, 27, 26, 28, 30, 17.5);
				});
				for (const [x, y, r] of [
					[
						18,
						30.6,
						2.2
					],
					[
						23.2,
						27,
						2.4
					],
					[
						28,
						21.4,
						2.1
					]
				]) ci(c, sp, x, y, r);
				el(c, B, 33, 11.5, 7.6, 6.2, -.7);
				f(c, "#ffc078", () => c.ellipse(31, 9.6, 3.4, 2, -.7, 0, TAU$3));
				ci(c, "#fff6c8", 35.4, 9.6, 1.9);
				ci(c, OUT, 35.8, 9.6, .9);
			}
		},
		vine: {
			zh: "藤蔓",
			d: (c, o) => {
				const P = (x) => {
					x.moveTo(12.5, 42);
					x.bezierCurveTo(4, 22, 31, 31, 26.5, 15.5);
					x.bezierCurveTo(25, 9.5, 31.5, 5.5, 35.5, 9.5);
				};
				for (const [x, y, r] of [
					[
						13,
						27,
						2.4
					],
					[
						36,
						26,
						-.7
					],
					[
						18.5,
						12.5,
						-2.2
					]
				]) at$2(c, x, y, 1, (k) => {
					el(k, "#7ddc3a", 0, 0, 7.4, 4, 0);
					el(k, "#b6f06a", -1, -1, 4, 1.4, 0);
				}, r);
				st$2(c, "#4f9a28", 6.6, P);
				st$2(c, "#8fd858", 1.8, (x) => {
					x.moveTo(11.5, 37);
					x.bezierCurveTo(8, 25.5, 27, 30, 24.6, 17.5);
				});
				ci(c, "#e0405a", 36.6, 10.6, 4.4);
				ci(c, "#ffb0b8", 35.6, 9.4, 1.5);
				if (!o.small) for (const [x, y] of [[22.5, 26.5], [28.6, 21]]) poly(c, "#e9e3cf", [
					[x, y],
					[x + 4.4, y + 1.6],
					[x + .6, y + 3]
				]);
			}
		},
		totem: {
			zh: "圖騰（戰意、吸引、高台）",
			d: (c, o, T) => {
				totemPole(c, o);
				if (T) {
					rr(c, T[0], 16.5, 19.6, 15, 4.2, 1);
					f(c, T[1], () => c.rect(16.5, 19.6, 4.4, 4.2));
					ci(c, T[0], 24, 5.4, 3.8);
					ci(c, T[1], 23, 4.4, 1.4);
				}
			}
		}
	});
	/** 狼頭（戰狼與狼人共用骨架：狼人多獠牙、鬃毛、紅眼）。 */
	function wolfHead(c, o, fur, dark, light, eye, were) {
		for (const s of [-1, 1]) {
			poly(c, fur, [
				[24 + s * 14.5, were ? 2.5 : 5],
				[24 + s * 5, 14.5],
				[24 + s * 14.5, 22]
			], .8);
			poly(c, were ? "#3a2a36" : "#e0a0a8", [
				[24 + s * 12.6, 8],
				[24 + s * 8.6, 14.5],
				[24 + s * 12.6, 17.5]
			]);
		}
		if (were) for (const s of [-1, 1]) poly(c, dark, [
			[24 + s * 12, 20],
			[24 + s * 20.5, 23.5],
			[24 + s * 15, 27],
			[24 + s * 19.5, 32],
			[24 + s * 11, 33]
		], .6);
		poly(c, fur, [
			[10.5, 17],
			[24, 10.5],
			[37.5, 17],
			[38, 27],
			[30.5, 37.5],
			[24, 41.5],
			[17.5, 37.5],
			[10, 27]
		], 1.2);
		poly(c, mix(fur, "#ffffff", .35), [
			[10.5, 17],
			[24, 10.5],
			[24, 14],
			[14, 19.5],
			[13, 27],
			[10, 27]
		]);
		poly(c, light, [
			[18, 25.5],
			[30, 25.5],
			[29, 35.5],
			[24, 40.5],
			[19, 35.5]
		], .6);
		poly(c, "#2a2230", [
			[21.2, 34.6],
			[26.8, 34.6],
			[24, 38.4]
		], .5);
		poly(c, eye, [
			[14.5, 20.4],
			[21.4, 23.4],
			[20.6, 26],
			[15.4, 24.6]
		], .3);
		poly(c, eye, [
			[33.5, 20.4],
			[26.6, 23.4],
			[27.4, 26],
			[32.6, 24.6]
		], .3);
		if (!o.small) {
			ci(c, OUT, 18.6, 23.6, 1);
			ci(c, OUT, 29.4, 23.6, 1);
		}
		if (were) {
			poly(c, "#ffffff", [
				[19.4, 37.4],
				[22, 37.6],
				[20.4, 42.6]
			], .2);
			poly(c, "#ffffff", [
				[28.6, 37.4],
				[26, 37.6],
				[27.6, 42.6]
			], .2);
			f(c, dark, () => c.rect(13.5, 17.6, 21, 2));
		}
	}
	table()({
		bear: {
			zh: "熊",
			d: (c, o) => {
				for (const x of [12, 36]) {
					ci(c, "#8a5a32", x, 11.5, 6.2);
					ci(c, "#d8a878", x, 12, 3);
				}
				ci(c, "#a06a36", 24, 25.5, 16);
				f(c, "#bd8850", () => c.ellipse(17.5, 16.5, 7, 4.4, -.5, 0, TAU$3));
				f(c, SH, () => {
					c.arc(24, 25.5, 16, -.2, 1.7);
					c.closePath();
				});
				el(c, "#ecd2a8", 24, 31.5, 8.6, 6.8);
				el(c, "#2a1c14", 24, 28.6, 3.4, 2.4);
				eyes(c, 17, 31, 22, 2, 2.2, "#2a1c14");
				if (!o.small) {
					st$2(c, "#2a1c14", 1.3, (x) => {
						x.moveTo(24, 30.6);
						x.lineTo(24, 33.4);
						x.moveTo(21, 34.6);
						x.quadraticCurveTo(24, 36.6, 27, 34.6);
					});
					ci(c, "#ffffff", 17.5, 21.4, .7);
					ci(c, "#ffffff", 31.5, 21.4, .7);
				}
			}
		},
		cat: {
			zh: "貓",
			d: (c, o) => {
				for (const s of [-1, 1]) {
					poly(c, "#f5ad4e", [
						[24 + s * 15.5, 4.5],
						[24 + s * 4, 14],
						[24 + s * 14.5, 23]
					], .9);
					poly(c, "#ffc8c0", [
						[24 + s * 13.4, 8.6],
						[24 + s * 8, 14.5],
						[24 + s * 13, 18.5]
					]);
				}
				el(c, "#f5ad4e", 24, 27, 16, 13.5);
				f(c, "#ffc878", () => c.ellipse(16.5, 20.5, 6, 3.6, -.5, 0, TAU$3));
				for (const x of [
					20,
					24,
					28
				]) poly(c, "#d07a20", [
					[x - 1.2, 14.4],
					[x + 1.2, 14.4],
					[x, 19.6]
				]);
				el(c, "#fff6e6", 24, 33.4, 6.6, 4.4);
				poly(c, "#ff8a9a", [
					[22.2, 30.2],
					[25.8, 30.2],
					[24, 32.6]
				], .3);
				eyes(c, 17, 31, 26, 3, 3.4, "#b6f06a");
				eyes(c, 17, 31, 26, .9, 3, OUT);
				if (!o.small) for (const s of [-1, 1]) {
					ln(c, "#fff6e6", 1, [[24 + s * 7, 33], [24 + s * 16.5, 31]]);
					ln(c, "#fff6e6", 1, [[24 + s * 7, 35], [24 + s * 16, 36.6]]);
				}
			}
		},
		werewolf: {
			zh: "狼人",
			d: (c, o) => wolfHead(c, o, "#6f7a86", "#4a525c", "#c8d0d8", "#ff5a4a", true)
		},
		demon: {
			zh: "惡魔",
			d: (c, o) => {
				for (const s of [-1, 1]) f(c, "#e9e3cf", () => {
					c.moveTo(24 + s * 7, 15);
					c.quadraticCurveTo(24 + s * 9, 6, 24 + s * 19.5, 3.5);
					c.quadraticCurveTo(24 + s * 17.5, 12, 24 + s * 14.5, 17.5);
					c.closePath();
				});
				poly(c, "#d8453a", [
					[10.5, 15],
					[37.5, 15],
					[36.5, 28.5],
					[24, 43],
					[11.5, 28.5]
				], 2);
				poly(c, "#f07a66", [
					[11, 15.6],
					[22, 15.6],
					[14.5, 28],
					[12, 27.6]
				]);
				poly(c, SH, [
					[30.5, 15],
					[38.5, 15],
					[37.5, 29],
					[26, 42],
					[24, 43]
				]);
				poly(c, "#ffd23f", [
					[13.5, 20.6],
					[21.6, 24.6],
					[20.4, 27],
					[14.6, 25.4]
				], .3);
				poly(c, "#ffd23f", [
					[34.5, 20.6],
					[26.4, 24.6],
					[27.6, 27],
					[33.4, 25.4]
				], .3);
				f(c, "#3a0c0c", () => c.rect(18.4, 32, 11.2, 2.2));
				poly(c, "#ffffff", [
					[18.6, 32],
					[21.4, 32],
					[20, 36.4]
				]);
				poly(c, "#ffffff", [
					[26.6, 32],
					[29.4, 32],
					[28, 36.4]
				]);
				if (!o.small) {
					ci(c, OUT, 18.6, 24.4, .9);
					ci(c, OUT, 29.4, 24.4, .9);
				}
			}
		},
		dragon: {
			zh: "龍",
			d: (c, o) => {
				f(c, "#e9e3cf", () => {
					c.moveTo(15, 14);
					c.quadraticCurveTo(8, 12, 3.5, 4);
					c.quadraticCurveTo(13, 5, 21, 11.5);
					c.closePath();
				});
				poly(c, "#4fae5a", [
					[6.5, 22],
					[16.5, 11.5],
					[29, 12],
					[43, 21.5],
					[44, 27.5],
					[30, 29.5],
					[8.5, 31.5]
				], 1.3);
				poly(c, "#3a8a46", [
					[7, 30],
					[26, 30.5],
					[40, 34],
					[38, 39.6],
					[22, 41],
					[10, 38.6]
				], 1.3);
				poly(c, "#8fd88a", [
					[16.5, 11.5],
					[29, 12],
					[36, 16.6],
					[18, 16]
				]);
				poly(c, "#fff6c8", [
					[14, 30],
					[17, 35],
					[20, 30.2],
					[23, 35],
					[26, 30.4],
					[29, 35],
					[32, 30.6],
					[35, 34.6],
					[38, 31]
				]);
				el(c, "#ffd23f", 24.5, 20, 3.6, 3);
				el(c, OUT, 24.9, 20, 1.1, 2.6);
				ci(c, "#1e4a26", 39.6, 22.6, 1.3);
				if (!o.small) for (const x of [9.5, 13.5]) poly(c, "#e9e3cf", [
					[x, 21],
					[x + 2.8, 14.5],
					[x + 4.6, 20]
				]);
			}
		},
		elemental: {
			zh: "元素化身",
			d: (c, _o) => {
				st$2(c, "#c8f0ff", 2.6, (x) => x.arc(24, 25, 14, 0, TAU$3));
				poly(c, "#e8fbff", [
					[24, 13.5],
					[32, 25],
					[24, 36.5],
					[16, 25]
				], .8);
				poly(c, "#8fe3ff", [
					[24, 13.5],
					[32, 25],
					[24, 36.5]
				]);
				ci(c, "#ffffff", 21.6, 22, 1.8);
				ci(c, "#ff6a1a", 24, 9, 6.8);
				ci(c, "#ffd23f", 23, 8.4, 3);
				ci(c, "#4aa8ff", 10.5, 34, 6.8);
				ci(c, "#cfe8ff", 9.4, 33, 2.8);
				ci(c, "#fff36b", 37.5, 34, 6.8);
				ci(c, "#ffffff", 36.4, 33, 2.8);
			}
		},
		giant: {
			zh: "巨人",
			d: (c, o) => {
				const S = "#e0b488";
				f(c, S, () => {
					c.moveTo(4, 42);
					c.bezierCurveTo(2.5, 24, 9, 16, 17, 16);
					c.lineTo(31, 16);
					c.bezierCurveTo(39, 16, 45.5, 24, 44, 42);
					c.closePath();
				});
				c.save();
				c.beginPath();
				c.rect(0, 0, 48, 42);
				c.clip();
				f(c, mix(S, "#ffffff", .35), () => c.ellipse(11.5, 24, 5, 7.6, .3, 0, TAU$3));
				f(c, SH, () => c.ellipse(41, 34, 6.5, 14, -.15, 0, TAU$3));
				f(c, "#8a5a32", () => {
					c.moveTo(12, 16.5);
					c.lineTo(18, 16.5);
					c.lineTo(37, 42);
					c.lineTo(30, 42);
					c.closePath();
				});
				c.restore();
				const arms = (k) => {
					for (const s of [-1, 1]) {
						st$2(k, S, 8.4, (x) => {
							x.moveTo(24 + s * 15.5, 25);
							x.lineTo(24 + s * 17.5, 12.5);
						});
						ci(k, S, 24 + s * 17.2, 9.6, 5.6);
						f(k, mix(S, "#ffffff", .35), () => k.ellipse(24 + s * 17.2 - 1.6, 7.6, 2.4, 1.5, -.5, 0, TAU$3));
					}
				};
				if (o.small) halo(c, o, arms);
				else arms(c);
				poly(c, "#8a5a32", [
					[14.6, 15.5],
					[33.4, 15.5],
					[32.6, 25],
					[24, 32.5],
					[15.4, 25]
				], 1.6);
				ci(c, S, 24, 13.4, 9.2);
				f(c, mix(S, "#ffffff", .35), () => c.ellipse(20.4, 7.6, 3.6, 2, -.4, 0, TAU$3));
				poly(c, "#8a5a32", [
					[15.2, 17],
					[20, 18.6],
					[24, 17.4],
					[28, 18.6],
					[32.8, 17],
					[32.4, 25],
					[24, 32.5],
					[15.6, 25]
				], 1.2);
				f(c, "#b98048", () => c.ellipse(19.6, 22, 2, 3.4, .3, 0, TAU$3));
				rr(c, "#5e3b1f", 16.4, 9.8, 15.2, 3.2, 1.3);
				eyes(c, 20.2, 27.8, 14.8, 1.5, 1.7, "#2a1c14");
				if (!o.small) {
					el(c, "#c8946a", 24, 16.4, 1.9, 1.5);
					ci(c, "#e8bb48", 31.5, 36, 2.2);
				}
			}
		},
		roc: {
			zh: "巨鵰",
			d: (c, _o) => {
				poly(c, "#a06a36", [
					[6.5, 31],
					[28.5, 28],
					[29.5, 42],
					[17, 39.6],
					[8, 42]
				], 1.2);
				poly(c, "#7e5a30", [
					[9, 34.5],
					[13, 38.5],
					[17, 34.5],
					[21, 38.5],
					[25, 34.5],
					[27.6, 38],
					[28.5, 41.6],
					[9, 41.6]
				]);
				poly(c, "#f2ead8", [
					[9.5, 33],
					[8.5, 17.5],
					[17.5, 7.5],
					[29.5, 7.5],
					[36, 13.5],
					[35.5, 23],
					[28, 25],
					[27, 33]
				], 1.6);
				poly(c, "#ffffff", [
					[9.6, 18],
					[17.6, 8.6],
					[22, 8.6],
					[13.6, 19],
					[13, 30],
					[10.5, 30]
				]);
				f(c, "#f0b030", () => {
					c.moveTo(33.5, 12.5);
					c.quadraticCurveTo(45.5, 15, 44, 23);
					c.quadraticCurveTo(43, 29, 39.5, 31);
					c.quadraticCurveTo(39.6, 25, 33, 23.5);
					c.closePath();
				});
				f(c, "#c88a1a", () => {
					c.moveTo(33, 23.5);
					c.quadraticCurveTo(39.6, 25, 39.5, 31);
					c.quadraticCurveTo(37, 27, 33, 26);
					c.closePath();
				});
				ci(c, "#ffd23f", 26.5, 15.5, 3.3);
				ci(c, OUT, 27, 15.5, 1.6);
				f(c, "#7e5a30", () => {
					c.moveTo(20.5, 10.6);
					c.lineTo(31, 12.4);
					c.lineTo(30.6, 14);
					c.lineTo(20.5, 12.4);
					c.closePath();
				});
			}
		},
		shadow: {
			zh: "暗影形態",
			d: (c, _o) => {
				for (const [x, y, a] of [[
					8.6,
					22.5,
					-.35
				], [
					39.4,
					22.5,
					.35
				]]) at$2(c, x, y, 1, (k) => {
					flame$1(k, "#7a4ec0", 0, 0, .7);
					flame$1(k, "#c8a8ff", .2, 2, .36);
				}, a);
				const B = (x) => {
					x.moveTo(4.5, 43);
					x.bezierCurveTo(4.5, 32, 10, 27.5, 18.6, 26);
					x.lineTo(18.6, 22.5);
					x.bezierCurveTo(12.5, 18.5, 13, 4.5, 24, 4.5);
					x.bezierCurveTo(35, 4.5, 35.5, 18.5, 29.4, 22.5);
					x.lineTo(29.4, 26);
					x.bezierCurveTo(38, 27.5, 43.5, 32, 43.5, 43);
					x.closePath();
				};
				f(c, "#8a5ad0", () => B(c));
				c.save();
				c.beginPath();
				B(c);
				c.clip();
				f(c, "#b48aee", () => c.ellipse(17, 10, 5, 7.5, .5, 0, TAU$3));
				f(c, "#b48aee", () => c.ellipse(10, 33, 4, 7, .5, 0, TAU$3));
				f(c, "#5a3590", () => c.ellipse(36, 30, 9, 16, -.2, 0, TAU$3));
				f(c, "#5a3590", () => c.ellipse(24, 25, 6.5, 2.6, 0, 0, TAU$3));
				c.restore();
				poly(c, "#ffe14d", [
					[16.6, 12.4],
					[22.6, 15],
					[21.8, 17.6],
					[17.2, 16.4]
				], .3);
				poly(c, "#ffe14d", [
					[31.4, 12.4],
					[25.4, 15],
					[26.2, 17.6],
					[30.8, 16.4]
				], .3);
			}
		},
		treant: {
			zh: "樹人",
			d: (c, o) => {
				poly(c, "#8a5a32", [
					[15, 17],
					[33, 17],
					[35.5, 42.5],
					[29.5, 39],
					[24, 43],
					[18.5, 39],
					[12.5, 42.5]
				], 1);
				f(c, "#b98048", () => c.rect(15.5, 18, 4, 21));
				f(c, SH, () => c.rect(29, 18, 4.4, 21));
				for (const [x, y, r] of [
					[
						13.5,
						13.5,
						8.6
					],
					[
						34.5,
						13.5,
						8.6
					],
					[
						24,
						9.5,
						10
					]
				]) ci(c, "#4f9a28", x, y, r);
				for (const [x, y, r] of [
					[
						11.5,
						10.5,
						4
					],
					[
						21.5,
						5.6,
						4.6
					],
					[
						33,
						10.5,
						3.4
					]
				]) ci(c, "#8fd858", x, y, r);
				eyes(c, 20, 28, 26, 2.3, 2.8, "#ffe14d");
				f(c, "#2a1c14", () => c.ellipse(24, 33.5, 3.2, 2.4, 0, 0, TAU$3));
				if (!o.small) {
					eyes(c, 20, 28, 26, .8, 1.6, OUT);
					ci(c, "#e0405a", 36, 17.5, 1.8);
				}
			}
		}
	});
	var LIQUID = {
		earth: ["#f0b030", "#fff0b0"],
		water: ["#4aa8ff", "#cfe8ff"],
		poison: ["#7ddc3a", "#d6f59a"],
		holy: ["#ffd75e", "#fff6c8"],
		fire: ["#ff8a2a", "#ffd23f"]
	};
	/** 號角的中心線（二次曲線）：吹口在左下、喇叭口在右上；半寬從 1.9 漸寬到 7.6。 */
	var hornPt = (t) => {
		const [a, b, p] = [
			[6, 41],
			[8, 17],
			[28, 14]
		], u = 1 - t;
		return [u * u * a[0] + 2 * u * t * b[0] + t * t * p[0], u * u * a[1] + 2 * u * t * b[1] + t * t * p[1]];
	};
	var hornSide = (s) => {
		const P = [];
		for (let i = 0; i <= 16; i++) {
			const t = i / 16, [x, y] = hornPt(t), [x1, y1] = hornPt(Math.min(1, t + .01)), [x0, y0] = hornPt(Math.max(0, t - .01)), dx = x1 - x0, dy = y1 - y0, L = Math.hypot(dx, dy), w = 1.9 + 5.7 * t * t;
			P.push([x - dy / L * w * s, y + dx / L * w * s]);
		}
		return P;
	};
	var THINGS = table()({
		flask: {
			zh: "瓶",
			note: "陶瓶：圓肚、短頸、木塞、頸上一圈麻繩，瓶口流下一道液體（液體染色：油琥珀、水藍…）",
			d: (c, o, tint) => {
				const [L0, L1] = LIQUID[tint ?? ""] ?? LIQUID.water;
				at$2(c, 24, 24, 1, (q) => {
					q.translate(-24, -24);
					rr(q, "#d08050", 19, 9, 10, 13, 2);
					ci(q, "#d08050", 24, 30.5, 12.6);
					f(q, "#f0b080", () => q.ellipse(18.6, 25.4, 4.2, 6.2, .5, 0, TAU$3));
					f(q, SH, () => {
						q.arc(24, 30.5, 12.6, -.5, 1.9);
						q.arc(24, 30.5, 8.4, 1.9, -.5, true);
						q.closePath();
					});
					if (!o.small) f(q, "#e8a070", () => q.rect(20.2, 10, 2, 11));
					rr(q, "#e8a070", 17.6, 8.2, 12.8, 3.8, 1.8);
					rr(q, "#f2e6c8", 18.8, 15.2, 10.4, 2.6, 1);
					rr(q, "#e8c890", 19.6, 1.4, 8.8, 7.8, 1.8);
					f(q, "#fff0d0", () => q.rect(19.8, 2.2, 2.6, 5.8));
					f(q, L0, () => {
						q.moveTo(28.4, 9.4);
						q.quadraticCurveTo(33.6, 12, 33.4, 19);
						q.quadraticCurveTo(35.2, 25, 34.2, 30);
						q.lineTo(31.6, 29.6);
						q.quadraticCurveTo(32, 23, 30.4, 19.4);
						q.quadraticCurveTo(29.6, 13.6, 27.6, 12);
						q.closePath();
					});
					drop$2(q, L0, 33.2, 35.4, .5);
					if (!o.small) {
						el(q, L1, 32, 15.6, .8, 2.6, -.3);
						ci(q, L1, 32.4, 36.2, .9);
					}
				}, -.32);
			}
		},
		smoke_bomb: {
			zh: "煙霧彈",
			note: "紙包的圓彈（米褐色）、一道橫的深褐腰帶、頂上方的鐵口蓋，引信往左上、尾端一顆橘紅火星（第 2 版）",
			d: (c, o) => {
				st$2(c, "#4a3020", 2.8, (x) => {
					x.moveTo(20.6, 15);
					x.quadraticCurveTo(18.4, 9.6, 13.6, 9.2);
				});
				poly(c, "#ff6a1a", starPts(11.4, 8.4, 6.4, 2.6, 6, -.3), .4);
				poly(c, "#ffd23f", starPts(11.4, 8.4, 3.6, 1.5, 6, -.3));
				ci(c, "#ffffff", 11.4, 8.4, 1.3);
				ci(c, "#d8c8a0", 22, 29, 13.4);
				f(c, "#f2e6c8", () => c.ellipse(15.8, 23, 4.6, 3.2, -.6, 0, TAU$3));
				f(c, "rgba(90,70,40,0.32)", () => {
					c.arc(22, 29, 13.4, -.4, 2);
					c.arc(22, 29, 9, 2, -.4, true);
					c.closePath();
				});
				c.save();
				c.beginPath();
				c.arc(22, 29, 13.4, 0, TAU$3);
				c.clip();
				f(c, "#6a4420", () => {
					c.moveTo(8, 27.6);
					c.quadraticCurveTo(22, 35.4, 36, 27.6);
					c.lineTo(36, 32.2);
					c.quadraticCurveTo(22, 40, 8, 32.2);
					c.closePath();
				});
				if (!o.small) f(c, "#9a6a36", () => {
					c.moveTo(9, 28.6);
					c.quadraticCurveTo(22, 35.6, 35, 28.6);
					c.lineTo(35, 29.8);
					c.quadraticCurveTo(22, 36.8, 9, 29.8);
					c.closePath();
				});
				c.restore();
				rr(c, "#8d969f", 17.2, 13.4, 9.6, 4.2, 1);
				f(c, "#c3ccd6", () => c.rect(18.2, 14, 3, 1.4));
			}
		},
		roar: {
			zh: "吼聲（號角）",
			note: "象牙色的彎號角、金箍與金色喇叭口，口外兩道粗聲波",
			d: (c, o) => {
				const A = hornSide(1), B = hornSide(-1).reverse();
				poly(c, "#e9e3cf", [...A, ...B], .6);
				poly(c, "#b8ae92", [...hornSide(-1).slice(2).map(([x, y], _i) => [x, y]), ...hornSide(-.1).slice(2).reverse()]);
				for (const t of [.42, .7]) {
					const [x, y] = hornPt(t), [x1, y1] = hornPt(t + .02), a = Math.atan2(y1 - y, x1 - x), w = 1.9 + 5.7 * t * t + .9;
					at$2(c, x, y, 1, (q) => rr(q, "#e8bb48", -1.6, -w, 3.2, w * 2, 1), a);
				}
				const [bx, by] = hornPt(1), [px, py] = hornPt(.98), a = Math.atan2(by - py, bx - px);
				at$2(c, bx, by, 1, (q) => {
					el(q, "#e8bb48", 0, 0, 2.6, 8.4);
					el(q, "#7a5a1a", .6, 0, 1.3, 5.8);
				}, a);
				if (!o.small) ci(c, "#ffffff", 13.4, 25, 1.1);
				for (const [r, w] of [[6.4, 3], [11.6, 3.2]]) st$2(c, "#ffe9a8", w, (x) => x.arc(bx + 1, by, r + 3, a - .75, a + .75), "round");
			}
		},
		boot: {
			zh: "腳／靴",
			note: "踢出去的皮靴：靴尖朝右上、鋼包頭、深色鞋底，靴口一圈淺皮翻邊",
			d: (c, o) => at$2(c, 24, 24, 1, (q) => {
				q.translate(-24, -24);
				rr(q, M.leather, 11, 6, 14.6, 26, 4);
				f(q, M.leather, () => {
					q.moveTo(11, 22);
					q.lineTo(25, 22);
					q.quadraticCurveTo(40.6, 23, 41.6, 33.4);
					q.lineTo(41.6, 36.6);
					q.lineTo(11, 36.6);
					q.closePath();
				});
				f(q, "#c3ccd6", () => {
					q.moveTo(33, 24.6);
					q.quadraticCurveTo(41, 26.6, 41.6, 33.4);
					q.lineTo(41.6, 36.6);
					q.lineTo(33, 36.6);
					q.closePath();
				});
				f(q, "#ffffff", () => q.ellipse(36, 27.4, 2.2, 1.1, .4, 0, TAU$3));
				rr(q, "#4a3020", 9.6, 35.4, 33.4, 5.2, 2.2);
				if (!o.small) for (const x of [
					15,
					21,
					27,
					33,
					39
				]) ci(q, "#8d969f", x, 38, .9);
				rr(q, "#d8a868", 9.6, 4, 17.4, 6.6, 3);
				f(q, "#f2dcb0", () => q.rect(12, 4.8, 12, 1.8));
				f(q, HI, () => q.rect(14, 12, 2.4, 18));
				if (!o.small) ln(q, "#5e3b1f", 1.3, [[25, 22.4], [30.4, 22.8]]);
			}, -.5)
		},
		shoulder: {
			zh: "肩撞",
			note: "米白人形全身側影往右上衝（身體前傾、跨步、手臂收在胸前），頭在最上面，前肩一片比頭小的弧形鋼肩甲（圓頂朝右上），背後兩道速度線（第 2 版）",
			d: (c, o) => {
				const CR = "#f2e6c8", CRD = "#d8ccae";
				if (!o.small) for (const [y, w] of [[19, 6], [26, 4.6]]) rr(c, CR, 3, y, w, 2.4, 1.2);
				st$2(c, CRD, 6.4, (x) => {
					x.moveTo(17.6, 31);
					x.lineTo(10.4, 40.6);
				});
				st$2(c, CR, 6.6, (x) => {
					x.moveTo(18.6, 32);
					x.lineTo(27.6, 36.4);
					x.lineTo(25.8, 43.4);
				});
				st$2(c, CR, 12.4, (x) => {
					x.moveTo(17.6, 30.4);
					x.lineTo(31, 22.2);
				});
				halo(c, o, (x) => st$2(x, CR, 5, (q) => {
					q.moveTo(30.6, 26);
					q.lineTo(34.6, 32.4);
					q.lineTo(39.4, 29.6);
				}));
				halo(c, o, (x) => {
					ci(x, CR, 26, 10.6, 6.6);
					if (!o.small) f(x, "#ffffff", () => x.ellipse(23.6, 8.2, 2.2, 1.3, -.6, 0, TAU$3));
				});
				halo(c, o, (x) => at$2(x, 34, 21, 1, (q) => {
					f(q, "#9aa4b0", () => {
						q.moveTo(-5.6, .4);
						q.quadraticCurveTo(0, 2.8, 5.6, .4);
						q.lineTo(5, 3.4);
						q.quadraticCurveTo(0, 6, -5, 3.4);
						q.closePath();
					});
					f(q, "#7d8794", () => {
						q.moveTo(-5, 2.6);
						q.quadraticCurveTo(0, 5, 5, 2.6);
						q.lineTo(5, 3.4);
						q.quadraticCurveTo(0, 6, -5, 3.4);
						q.closePath();
					});
					f(q, "#c3ccd6", () => {
						q.ellipse(0, .4, 6.2, 5, 0, Math.PI, 0);
						q.quadraticCurveTo(0, 2.6, -6.2, .4);
						q.closePath();
					});
					f(q, "#ffffff", () => q.ellipse(-1.8, -2.4, 2.6, 1.1, -.2, 0, TAU$3));
				}, Math.PI / 3.2));
			}
		},
		fang: {
			zh: "獠牙",
			note: "暗紅的下顎肉一彎，兩根往上彎的大象牙色獠牙，中間一排小牙",
			d: (c, o) => {
				f(c, "#a83a3a", () => {
					c.moveTo(4.6, 30);
					c.quadraticCurveTo(24, 46, 43.4, 30);
					c.lineTo(43.4, 36.4);
					c.quadraticCurveTo(24, 50, 4.6, 36.4);
					c.closePath();
				});
				f(c, "#e06a5a", () => {
					c.moveTo(6, 30.8);
					c.quadraticCurveTo(24, 45.4, 42, 30.8);
					c.lineTo(42, 32.6);
					c.quadraticCurveTo(24, 47, 6, 32.6);
					c.closePath();
				});
				if (!o.small) for (const x of [
					19,
					24,
					29
				]) poly(c, "#f2ecd8", [
					[x - 2, 38.2],
					[x, 33.8],
					[x + 2, 38.2]
				], .3);
				for (const s of [-1, 1]) {
					const X = (v) => 24 + s * v;
					f(c, "#f2ecd8", () => {
						c.moveTo(X(9.6), 36.4);
						c.quadraticCurveTo(X(17), 22, X(9.6), 4);
						c.quadraticCurveTo(X(9), 18, X(3), 34.4);
						c.closePath();
					});
					f(c, s < 0 ? "#ffffff" : "#c8bfa0", () => {
						c.moveTo(X(8.6), 34);
						c.quadraticCurveTo(X(13.6), 22, X(9.6), 5.6);
						c.quadraticCurveTo(X(11.4), 20, X(6.4), 34.4);
						c.closePath();
					});
				}
			}
		},
		slime: {
			zh: "黏液",
			note: "一團洋紅色的黏液：圓頂、底下攤開成同色的一灘，團裡兩顆氣泡、左上亮點（第 2 版）",
			d: (c, o) => {
				const B = (x) => {
					x.moveTo(9, 41.8);
					x.quadraticCurveTo(4.2, 41.6, 4.6, 35.6);
					x.bezierCurveTo(5, 21.4, 13.4, 13, 22.6, 13.2);
					x.bezierCurveTo(31.4, 13.4, 36.4, 20.6, 36.4, 29.8);
					x.quadraticCurveTo(38, 34, 42.6, 35.4);
					x.quadraticCurveTo(46.2, 40.4, 41, 41.8);
					x.closePath();
				};
				const P = "#e05ab8", PL = "#ffb4ec", PD = "#9a2c7c";
				f(c, P, B);
				c.save();
				c.beginPath();
				B(c);
				c.clip();
				f(c, PD, () => c.ellipse(28, 41, 18, 4.2, -.06, 0, TAU$3));
				f(c, PD, () => c.ellipse(35.4, 27, 3.4, 9, .12, 0, TAU$3));
				c.restore();
				f(c, PL, () => c.ellipse(13.6, 20.4, 4.6, 3, -.8, 0, TAU$3));
				f(c, "#ffffff", () => c.ellipse(12.6, 19.4, 2, 1.1, -.8, 0, TAU$3));
				ci(c, PL, 25, 27, 3.2);
				ci(c, "#ffffff", 24.2, 26.2, 1.1);
				if (!o.small) {
					ci(c, PL, 16.4, 32.4, 1.8);
					f(c, PL, () => c.ellipse(40, 37.6, 2.2, .8, .3, 0, TAU$3));
				}
			}
		}
	});
	/** 一對短楔形（直線突刺、飛刃）：退到握把那一端的兩側、朝右上；底色用元素底的亮色（soft），中間一道細的亮芯，不用純白，長度是第 1 版的四成。
	*  寬度沒有再縮：規則 10 要最粗處 ≥ 顯示邊長 12%（底寬 11 單位），再窄就是細線。 */
	var wedges = (c, soft, A, core = .6) => {
		for (const [x, y] of [[4.6, 29.4], [18.6, 43.4]]) {
			poly(c, rgba(soft, .95), [
				[x - 3.9, y - 3.9],
				[x + 3.9, y + 3.9],
				[x + 11.5, y - 11.5]
			], .8);
			poly(c, rgba(A, core), [
				[x - .9, y - 2.3],
				[x + 1.4, y],
				[x + 7.6, y - 7.6]
			]);
		}
	};
	table()({
		swing: {
			zh: "揮砍",
			note: "一彎弧形刀光橫過作用端",
			d: (c, _o, A) => {
				f(c, rgba(A, .95), () => {
					c.moveTo(4.5, 25);
					c.quadraticCurveTo(24, -12, 46, 19);
					c.quadraticCurveTo(26, 6.5, 4.5, 25);
					c.closePath();
				});
				f(c, "#ffffff", () => {
					c.moveTo(11, 17.5);
					c.quadraticCurveTo(25, -3, 41.5, 13.6);
					c.quadraticCurveTo(26, 2.6, 11, 17.5);
					c.closePath();
				});
			}
		},
		thrust: {
			zh: "直線突刺",
			note: "握把那一端兩側各一道短楔形（元素底的亮色，不用白）",
			d: (c, _o, A, p) => p.weapon ? wedges(c, p.dim ?? A, A, .4) : wedges(c, p.soft ?? A, A)
		},
		sweep: {
			zh: "扇形橫掃",
			note: "從左下張開的扇面與亮邊",
			d: (c, _o, A) => {
				f(c, rgba(A, .5), () => {
					c.moveTo(5, 43);
					c.arc(5, 43, 40, -1.72, .14);
					c.closePath();
				});
				st$2(c, rgba(A, .98), 7, (x) => x.arc(5, 43, 36.5, -1.6, .02), "butt");
				st$2(c, "#ffffff", 2.2, (x) => x.arc(5, 43, 38, -1.5, -.5), "butt");
			}
		},
		spin: {
			zh: "迴旋",
			note: "繞一圈的粗圓弧加箭頭",
			d: (c, _o, A) => {
				st$2(c, rgba(A, .98), 7, (x) => x.arc(24, 24, 19.5, -.5, 4.2), "butt");
				st$2(c, "#ffffff", 2.2, (x) => x.arc(24, 24, 21, 1.2, 3.6), "butt");
				at$2(c, 24 + Math.cos(-.5) * 19.5, 24 + Math.sin(-.5) * 19.5, 1, (k) => poly(k, A, [
					[-7.5, 0],
					[7.5, 0],
					[0, -9.5]
				], .5), -.5 + Math.PI);
			}
		},
		shot: {
			zh: "射出",
			note: "元素道具後面拖一條粗彗尾；飛刃是兩側的短楔形；弓、弩、槍不畫出手線（作用端外側的閃光或記號就是射出去的那一下）",
			d: (c, _o, A, p) => {
				if (p.weapon) return;
				if (p.noTail) return;
				if (p.projectile) wedges(c, p.soft ?? A, A);
				else {
					const w = p.size * .25;
					poly(c, rgba(A, .95), [
						[p.x - w, p.y - w * .2],
						[p.x + w * .2, p.y + w],
						[1.5, 46.5]
					], .4);
					poly(c, "#ffffff", [
						[p.x - w * .55, p.y + w * .1],
						[p.x - w * .1, p.y + w * .55],
						[6, 42]
					]);
				}
			}
		},
		area: {
			zh: "範圍爆發",
			note: "道具後面一大片尖角爆開",
			d: (c, _o, A) => {
				poly(c, rgba(A, .62), starPts(24, 24, 23.5, 15.5, 10, -Math.PI / 2 + .31));
				poly(c, "rgba(255,255,255,0.55)", starPts(24, 24, 16.5, 11.5, 10, -Math.PI / 2 + .31));
			}
		},
		chain: {
			zh: "連鎖",
			note: "粗折線跳到第二個火花（包外框，畫在主體裡）",
			d: () => {}
		},
		place: {
			zh: "落點",
			note: "腳下一片發亮的圓地",
			d: (c, _o, A) => {
				el(c, rgba(A, .6), 24, 40.5, 21, 6.4);
				el(c, "rgba(255,255,255,0.7)", 24, 40.5, 13.5, 3.4);
			}
		},
		aura: {
			zh: "自身光環",
			note: "道具外面一圈粗光環",
			d: (c, _o, A, p) => {
				st$2(c, rgba(A, .5), 8.6, (x) => x.arc(p.x, p.y, Math.min(19.2, 20.6 - Math.max(Math.abs(p.x - 24), Math.abs(p.y - 24))), 0, TAU$3));
			}
		}
	});
	/** 衝刺的兩個 V（後面那個、前面那個的顏色）。預設米黃＋白；配肩撞時換成元素底的亮色（11-12 補道具第 2 版：米白 V 和米白人形黏成火箭）。 */
	var dashV = (c, cols) => {
		c.rotate(-Math.PI / 4);
		c.scale(.82, .82);
		for (const [x, col] of [[-5.8, cols[0]], [3.4, cols[1]]]) poly(c, col, [
			[x - 5.4, -7.8],
			[x + 2.6, -7.8],
			[x + 9, 0],
			[x + 2.6, 7.8],
			[x - 5.4, 7.8],
			[x + 1, 0]
		], .5);
	};
	var arrow$2 = (c, col, hi) => {
		poly(c, col, [
			[-10.5, -3.6],
			[-.5, -3.6],
			[-.5, -9.6],
			[10.5, 0],
			[-.5, 9.6],
			[-.5, 3.6],
			[-10.5, 3.6]
		], .5);
		poly(c, hi, [
			[-10.5, -3.6],
			[-.5, -3.6],
			[-.5, -9.6],
			[10.5, 0],
			[-10.5, 0]
		]);
	};
	var ACT = table()({
		hit: {
			zh: "傷害",
			side: "tr",
			note: "作用端一顆白色四芒閃光",
			d: (c, _o, T) => {
				poly(c, T[0], starPts(0, 0, 10.5, 3.6, 4), .4);
				poly(c, "#ffffff", starPts(0, 0, 6, 2.2, 4));
			},
			def: ["#ffffff", "#ffffff"]
		},
		combo: {
			zh: "追擊／連擊",
			side: "tr",
			note: "一大一小兩顆四芒閃光（大的白、小的染條件色）＝打兩下",
			d: (c, o, T) => {
				poly(c, "#ffffff", starPts(-2, -2, 9.2, 3.6, 4), .4);
				halo(c, o, (x) => {
					poly(x, T[0], starPts(4.2, 4.2, 7, 2.9, 4), .4);
					poly(x, T[1], starPts(4.2, 4.2, 3.3, 1.4, 4));
				}, OUT, .6);
			},
			def: ["#ffd23f", "#fff6c8"]
		},
		finisher: {
			zh: "終結",
			side: "tr",
			note: "一顆骷髏頭、紅眼",
			d: (c) => {
				rr(c, "#cfc8b0", -5.8, 3, 11.6, 8.2, 2.6);
				ci(c, "#f2ecd8", 0, -1.6, 9.6);
				f(c, "#ffffff", () => c.ellipse(-3.4, -6.6, 3.6, 2, -.5, 0, TAU$3));
				eyes(c, -3.8, 3.8, -.6, 2.9, 3.4, "#c8202a");
				poly(c, "#2a1c36", [
					[0, 3],
					[1.6, 6.2],
					[-1.6, 6.2]
				]);
				f(c, "#2a1c36", () => c.rect(-.5, 7.4, 1, 3.8));
			}
		},
		builder: {
			zh: "蓄積／蓄力",
			side: "bl",
			note: "三根越來越高的粗條",
			d: (c, _o, T) => {
				for (const [x, h] of [
					[-10.8, 8],
					[-3.5, 13.5],
					[3.8, 19.5]
				]) {
					rr(c, T[0], x, 9.6 - h, 6.8, h, 1.6);
					f(c, T[1], () => c.roundRect(x, 9.6 - h, 6.8, 3, [
						1.6,
						1.6,
						0,
						0
					]));
				}
			},
			def: ["#e8bb48", "#fff6c8"]
		},
		step: {
			zh: "瞬步",
			side: "self",
			note: "道具左下拖兩道紫色殘影，作用端一顆白閃光",
			d: () => {}
		},
		dash: {
			zh: "衝刺／跳躍",
			side: "bl",
			note: "兩個朝右上的粗 V 形箭頭",
			d: (c) => dashV(c, ["#ffe9a8", "#ffffff"])
		},
		knockdown: {
			zh: "擊倒",
			side: "tr",
			note: "黃色七角撞擊星壓在一條地面線上",
			d: (c) => {
				rr(c, "#b8862a", -11, 6.4, 22, 4.6, 2);
				poly(c, "#ffd23f", starPts(0, -1, 10.5, 5, 7, -1.2), .4);
				poly(c, "#ffffff", starPts(0, -1, 5, 2.5, 7, -1.2));
			}
		},
		push: {
			zh: "推開",
			side: "tr",
			note: "朝右上的黃白粗箭頭",
			d: (c) => {
				c.rotate(-Math.PI / 4);
				arrow$2(c, "#ffd23f", "#ffffff");
			}
		},
		pull: {
			zh: "拉近",
			side: "tr",
			note: "朝左下（往道具）的青色粗箭頭，尾端一個圓鉤",
			d: (c) => {
				c.rotate(Math.PI * .75);
				ci(c, "#6ae0ff", -9.5, 0, 4.6);
				arrow$2(c, "#6ae0ff", "#d8f8ff");
				ci(c, "#0b2f4e", -9.5, 0, 1.6);
			}
		},
		slow: {
			zh: "緩速",
			side: "tr",
			note: "一只懷錶（金殼、白面、兩根指針、頂上錶冠與提環）",
			d: (c) => {
				st$2(c, "#e8bb48", 2, (x) => x.arc(0, -8.5, 2, 0, TAU$3));
				rr(c, "#b8862a", -2.1, -7.6, 4.2, 3.6, 1);
				ci(c, "#e8bb48", 0, 2.4, 9);
				f(c, "#b8862a", () => {
					c.arc(0, 2.4, 9, -.2, 1.8);
					c.arc(0, 2.4, 6.3, 1.8, -.2, true);
					c.closePath();
				});
				ci(c, "#fff6e0", 0, 2.4, 6.3);
				f(c, "#ffffff", () => c.ellipse(-2.3, -.3, 2.5, 1.5, -.6, 0, TAU$3));
				ln(c, "#2a1c36", 1.9, [
					[0, -2.4],
					[0, 2.4],
					[3.5, 4.3]
				]);
				ci(c, "#2a1c36", 0, 2.4, 1.2);
			}
		},
		bind: {
			zh: "控制（冰凍、定身、暈眩、沉默）",
			side: "tr",
			note: "一把鎖（染狀態色）；緩速另用懷錶",
			d: (c, _o, T) => {
				st$2(c, T[1], 4.8, (x) => x.arc(0, -3, 5.2, Math.PI, 0), "butt");
				rr(c, T[0], -8.6, -3, 17.2, 13.4, 3.2);
				f(c, T[1], () => c.roundRect(-8.6, -3, 17.2, 4, [
					3.2,
					3.2,
					0,
					0
				]));
				ci(c, OUT, 0, 3, 2.3);
				f(c, OUT, () => c.rect(-1.1, 3.4, 2.2, 4.2));
			},
			def: ["#ffd84a", "#fff6c8"]
		},
		mark: {
			zh: "標記",
			side: "tr",
			note: "紅色空心環、上下左右四個缺口、中心一顆紅點（準星）",
			d: (c) => {
				ci(c, OUT, 0, 0, 8.4);
				for (let i = 0; i < 4; i++) st$2(c, "#ff4a5a", 4.4, (x) => x.arc(0, 0, 9.3, i * Math.PI / 2 + .13, (i + 1) * Math.PI / 2 - .13), "butt");
				st$2(c, "#ffc0c4", 1.5, (x) => x.arc(0, 0, 10, Math.PI + .3, Math.PI * 1.5 - .3), "butt");
				ci(c, "#ff4a5a", 0, 0, 3.5);
				ci(c, "#ffc0c4", -.9, -.9, 1.3);
			}
		},
		curse: {
			zh: "減益（虛弱、易傷、恐懼、致盲、挑釁）",
			side: "tr",
			note: "朝下的粗箭頭加一條頂槓（染狀態色；和增益的朝上箭頭相反）",
			d: (c, _o, T) => {
				poly(c, T[0], [
					[0, 11],
					[10, 1],
					[4, 1],
					[4, -4.4],
					[-4, -4.4],
					[-4, 1],
					[-10, 1]
				], .6);
				poly(c, T[1], [
					[-4, -4.4],
					[0, -4.4],
					[0, 11],
					[-10, 1],
					[-4, 1]
				]);
				rr(c, T[0], -4.6, -10.8, 9.2, 4.4, 1.6);
			},
			def: ["#9a6ad8", "#d2b0ff"]
		},
		dot: {
			zh: "持續傷害（燃燒、中毒、流血）",
			side: "tr",
			note: "燃燒是一團火，中毒與流血是一大一小兩滴；道具是武器時只留一顆、縮小、放在作用端外側",
			d: (c, _o, T, t, one) => {
				if (t === "fire") {
					flame$1(c, "#ff6a1a", 0, 0, 1.08);
					flame$1(c, "#ffd23f", .4, 2.6, .64);
				} else if (one) {
					drop$2(c, T[0], 0, 0, 1.12);
					f(c, T[1], () => c.ellipse(-2.6, 2.4, 1.9, 3.8, .4, 0, TAU$3));
				} else {
					drop$2(c, T[0], -2.6, 1, .98);
					f(c, T[1], () => c.ellipse(-5, 3, 1.6, 3.4, .4, 0, TAU$3));
					drop$2(c, T[0], 6.6, -5, .52);
				}
			},
			def: TINT.poison
		},
		heal: {
			zh: "治療",
			side: "bl",
			note: "綠色粗十字",
			d: (c) => {
				rr(c, "#4fd07a", -3.7, -10.5, 7.4, 21, 2.2);
				rr(c, "#4fd07a", -10.5, -3.7, 21, 7.4, 2.2);
				f(c, "#c8ffd8", () => c.roundRect(-3.7, -10.5, 7.4, 5, [
					2.2,
					2.2,
					0,
					0
				]));
				f(c, "#c8ffd8", () => c.roundRect(-10.5, -3.7, 6.8, 3, [
					2.2,
					0,
					0,
					0
				]));
				f(c, "#ffffff", () => c.rect(-2.4, -9, 1.6, 6));
			}
		},
		shield: {
			zh: "護盾",
			side: "bl",
			note: "淡藍小盾",
			d: (c, _o, T) => {
				poly(c, T[0], [
					[-9.4, -9.6],
					[9.4, -9.6],
					[8.8, 2],
					[0, 10],
					[-8.8, 2]
				], 1);
				poly(c, T[1], [
					[-9.4, -9.6],
					[0, -9.6],
					[0, 10],
					[-8.8, 2]
				], 1);
				rr(c, "#ffffff", -1.4, -7, 2.8, 13, 1);
				rr(c, "#ffffff", -6, -3.4, 12, 2.8, 1);
			},
			def: ["#6ab8f0", "#cfe8ff"]
		},
		buff: {
			zh: "增益",
			side: "bl",
			note: "朝上的粗箭頭加一條底槓",
			d: (c, _o, T) => {
				poly(c, T[0], [
					[0, -11],
					[10, -1],
					[4, -1],
					[4, 4.4],
					[-4, 4.4],
					[-4, -1],
					[-10, -1]
				], .6);
				poly(c, T[1], [
					[0, -11],
					[-10, -1],
					[-4, -1],
					[-4, 4.4],
					[0, 4.4]
				]);
				rr(c, T[0], -4.6, 6.4, 9.2, 4.4, 1.6);
			},
			def: ["#ffb23a", "#fff6c8"]
		},
		summon: {
			zh: "召喚",
			side: "tr",
			note: "一隻小小的靈（染召喚物的元素色；道具已經是召喚物時不畫，改成腳下的落點）",
			d: (c, o, T) => {
				c.save();
				c.scale(.5, .5);
				c.translate(-24.6, -24);
				spiritArt(c, {
					...o,
					small: true
				}, T);
				c.restore();
			},
			def: ["#5fd8c8", "#dcfff8"]
		},
		transform: {
			zh: "化身",
			side: "self",
			note: "頭像兩側各一道繞圈的粗弧箭頭",
			d: () => {}
		},
		surface: {
			zh: "地面效果（火、水、冰、毒、油、煙、暗、聖）與地形／障礙",
			side: "tr",
			note: "液體（水、毒、油）：一灘扁平的水漬上面落下一大滴；聖光：地上一圈光；煙、暗霧：兩團雲；冰：薄冰加冰刺；火：餘燼上三撮火苗；地形／障礙（灰石色）：地上兩塊石頭",
			d: (c, o, T, t) => {
				if (t === "stone") {
					el(c, "#8c8474", 0, 7.6, 11.6, 3.8);
					poly(c, T[0], [
						[-9, 7.6],
						[-7.6, -3],
						[-1.6, -9.2],
						[5.4, -5],
						[7, 7.6]
					], 1.2);
					poly(c, T[1], [
						[-7.4, -3],
						[-1.6, -9],
						[5.2, -5],
						[-1, -1.4]
					], .5);
					poly(c, "#8c8474", [
						[-1, -1.4],
						[5.3, -4.8],
						[6.8, 7.4],
						[.4, 7.4]
					], .5);
					poly(c, T[0], [
						[3.2, 8],
						[4.8, 1.8],
						[9.2, .8],
						[10.4, 8]
					], 1);
					poly(c, T[1], [
						[5, 2],
						[9, 1.1],
						[8.4, 3.8],
						[5.8, 4.4]
					], .3);
					return;
				}
				const dk = mix(T[0], "#16121a", .3);
				if (t === "holy") {
					el(c, T[0], 0, 4.4, 11.6, 6.6);
					el(c, T[1], 0, 3.2, 10.2, 4.8);
					el(c, "#c8861a", 0, 4.6, 6.4, 2.7);
					halo(c, o, (x) => {
						poly(x, T[0], starPts(0, -6.6, 5, 1.9, 4), .3);
						poly(x, "#ffffff", starPts(0, -6.6, 2.6, 1, 4));
					}, OUT, .5);
					return;
				}
				if (t === "steel" || t === "shadow") {
					const cloud = (c2, col, hi, x, y, k) => at$2(c2, x, y, k, (q) => {
						ci(q, col, -4.6, 1.6, 4.4);
						ci(q, col, .6, -1.4, 5.6);
						ci(q, col, 5.6, 2, 3.8);
						rr(q, col, -9, 1.6, 18.4, 4.8, 2.4);
						if (hi) el(q, hi, -.6, -3.6, 3.2, 1.5, -.3);
					});
					cloud(c, mix(T[0], "#16121a", .2), null, 4.6, -4.4, .72);
					halo(c, o, (x) => {
						cloud(x, T[0], T[1], -2.2, 3.6, 1);
						f(x, dk, () => x.roundRect(-11.2, 7.6, 18.4, 2.4, [
							0,
							0,
							2.4,
							2.4
						]));
					}, OUT, .6);
					return;
				}
				if (t === "ice") {
					poly(c, T[0], [
						[-10.7, 6.6],
						[-7, 3],
						[4, 2.2],
						[10.7, 5.8],
						[8, 9.8],
						[-5.4, 10.2]
					], .8);
					poly(c, T[1], [
						[-9, 6.4],
						[-6.4, 4],
						[3.2, 3.4],
						[-2, 6.6]
					], .3);
					poly(c, dk, [
						[10.2, 6.2],
						[7.8, 9.4],
						[-5, 9.8],
						[1, 7.6]
					], .3);
					poly(c, T[0], [
						[-7.6, 5.4],
						[-4.2, -6.4],
						[-.6, 5.4]
					], .5);
					poly(c, T[0], [
						[-.4, 5.6],
						[4.6, -10.6],
						[8.6, 5.6]
					], .5);
					poly(c, T[1], [
						[-7, 5.2],
						[-4.2, -5.4],
						[-4.2, 5.2]
					]);
					poly(c, T[1], [
						[.4, 5.4],
						[4.6, -9.4],
						[4.6, 5.4]
					]);
					return;
				}
				if (t === "fire") {
					el(c, "#8a3410", 0, 7.8, 11.6, 3.4);
					el(c, "#c2531c", -1, 7, 8.6, 1.5);
					for (const [x, y, k] of [
						[
							-6.6,
							2.6,
							.5
						],
						[
							6.4,
							3,
							.46
						],
						[
							0,
							-.6,
							.72
						]
					]) {
						flame$1(c, T[0], x, y, k);
						flame$1(c, T[1], x + .2, y + 2.6 * k, k * .55);
					}
					return;
				}
				el(c, T[0], 0, 6.6, 11.6, 4.5);
				ci(c, T[0], -8.3, 5.4, 3.2);
				ci(c, T[0], 8.2, 7.6, 3.2);
				el(c, T[0], 4.4, 4.2, 4.6, 2.6);
				el(c, T[1], -2.6, 6, 5.6, 1.5);
				drop$2(c, T[0], -2.4, -4.6, .7);
				f(c, T[1], () => c.ellipse(-3.6, -3.4, 1.2, 2.5, .4, 0, TAU$3));
			},
			def: TINT.water
		},
		trap: {
			zh: "陷阱／符文",
			side: "tr",
			note: "張開的捕獸夾（正面看）：一條深色底板上四根朝上的鋼牙，左右對稱",
			d: (c) => {
				for (const x of [
					-7.8,
					-2.6,
					2.6,
					7.8
				]) {
					poly(c, "#f2f5f8", [
						[x - 2.9, 6.4],
						[x, -10.8],
						[x + 2.9, 6.4]
					], .4);
					poly(c, "#aab3bd", [
						[x, -9.6],
						[x + 2.7, 6.4],
						[x, 6.4]
					]);
				}
				rr(c, "#5a6169", -11.2, 4.8, 22.4, 6.4, 2.2);
				f(c, "#8d969f", () => c.roundRect(-11.2, 4.8, 22.4, 2, [
					2.2,
					2.2,
					0,
					0
				]));
			}
		},
		detonate: {
			zh: "引爆／獻祭",
			side: "tr",
			note: "橘色十角爆炸、黃白芯",
			d: (c, _o, T) => {
				poly(c, T[0], starPts(0, 0, 11, 6.2, 10), .4);
				poly(c, "#ffd23f", starPts(0, 0, 7.4, 3.8, 10, -Math.PI / 2 + .31));
				ci(c, "#ffffff", 0, 0, 2.6);
			},
			def: ["#ff7a2a", "#ffd23f"]
		},
		modify: {
			zh: "修正",
			side: "bl",
			note: "一顆齒輪（染改動的種類）",
			d: (c, _o, T) => {
				for (let i = 0; i < 8; i++) {
					c.save();
					c.rotate(i * Math.PI / 4);
					rr(c, T[0], -2.6, -11.4, 5.2, 6, 1);
					c.restore();
				}
				ci(c, T[0], 0, 0, 8.4);
				f(c, T[1], () => {
					c.arc(0, 0, 8.4, 3.5, 5.2);
					c.arc(0, 0, 5.6, 5.2, 3.5, true);
					c.closePath();
				});
				ci(c, OUT, 0, 0, 3.2);
			},
			def: ["#e8bb48", "#fff6c8"]
		}
	});
	/** 記號的位置：記號外形在 ±11.6 單位以內，放大 k 倍後離主圖格邊緣留 2.6 單位（外框才不會被格子切掉）。 */
	var corner = (side, k) => {
		const a = 2.6 + 11.6 * k;
		return side === "bl" ? [a, 48 - a] : [48 - a, a];
	};
	corner("tr", 1.06);
	corner("bl", 1.06);
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/qIcon/parts.ts
	/** 樣張 `QIcons` 用到的部分。 */
	var Q = {
		ART,
		render,
		outlinePx
	};
	/** 樣張 `QIconsWeapons` 用到的部分。 */
	var QW = { blit };
	var PI$1 = Math.PI;
	var CREAM$1 = "#f2e6c8";
	var ALLY = "#7de0a8";
	var ENEMY = "#ff5a5a";
	var STEEL = "#c3ccd6";
	var GOLD$1 = "#e8bb48";
	var LILAC = "#c8a0d8";
	var STONE$1 = "#b4ac9a";
	var STONE_L$1 = "#ece6d6";
	var STONE_D$1 = "#8c8474";
	var INK = "#2a1c36";
	var st$1 = (c, col, w, fn, cap = "round") => {
		c.beginPath();
		fn(c);
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = cap;
		c.lineJoin = "round";
		c.stroke();
	};
	var at$1 = (c, x, y, k, fn, rot = 0) => {
		c.save();
		c.translate(x, y);
		c.rotate(rot);
		c.scale(k, k);
		fn(c);
		c.restore();
	};
	/** 第 3 批的效果記號（同一個題材同一個形，直接呼叫）。 */
	var act$1 = (id, T, t) => (c, o) => ACT[id].d(c, o, T ?? ACT[id].def ?? ["#ffd23f", "#ffffff"], t);
	/** 畫在 48 格的既有圖樣：縮到 ±10 單位的座標裡。 */
	var from48 = (d, k = .47) => (c, o) => {
		c.save();
		c.scale(k, k);
		c.translate(-24, -24);
		d(c, o);
		c.restore();
	};
	/** 人形（規則 9：單色剪影，圓頭加圓肩的半身）；高約 15k。 */
	var bust = (c, col, x, y, k = 1) => {
		ci(c, col, x, y - 4.6 * k, 3.7 * k);
		f(c, col, () => {
			c.moveTo(x - 6.2 * k, y + 7 * k);
			c.quadraticCurveTo(x - 6.2 * k, y - .4 * k, x, y - .4 * k);
			c.quadraticCurveTo(x + 6.2 * k, y - .4 * k, x + 6.2 * k, y + 7 * k);
			c.closePath();
		});
	};
	/** 朝右的細長箭頭（高 11.2）。 */
	var arrowS = (c, col, hi) => {
		poly(c, col, [
			[-10, -2.4],
			[1, -2.4],
			[1, -5.6],
			[10, 0],
			[1, 5.6],
			[1, 2.4],
			[-10, 2.4]
		], .4);
		if (hi) poly(c, hi, [
			[-10, -2.4],
			[1, -2.4],
			[1, -5.6],
			[10, 0],
			[-10, 0]
		]);
	};
	var heart$1 = (c, col, x, y, s) => {
		c.save();
		c.translate(x, y);
		c.scale(s, s);
		c.beginPath();
		c.moveTo(0, 7);
		c.bezierCurveTo(-11, -1, -7, -10, 0, -4.5);
		c.bezierCurveTo(7, -10, 11, -1, 0, 7);
		c.closePath();
		c.fillStyle = col;
		c.fill();
		c.restore();
	};
	var heartArt = (c, _o, col = "#f0503e", hi = "#ffb0a0", s = 1.25) => {
		heart$1(c, col, 0, 1.4, s);
		el(c, hi, -3.6 * (s / 1.25), -2.6 * (s / 1.25), 2.6, 1.7, -.6);
	};
	var plus$1 = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => {
		rr(q, col, x - 1.5 * k, y - 4.4 * k, 3 * k, 8.8 * k, .8 * k);
		rr(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, .8 * k);
	});
	var minus = (c, o, x, y, k = 1, col = "#ffffff") => halo(c, o, (q) => rr(q, col, x - 4.4 * k, y - 1.5 * k, 8.8 * k, 3 * k, .8 * k));
	var star4 = (c, col, x, y, R, core = "#ffffff") => {
		poly(c, col, starPts(x, y, R, R * .36, 4), .3);
		if (core) poly(c, core, starPts(x, y, R * .55, R * .2, 4));
	};
	var burstStar = (c, x, y, R, col = "#ffd23f") => {
		poly(c, col, starPts(x, y, R, R * .48, 7, -1.2), .3);
		poly(c, "#ffffff", starPts(x, y, R * .48, R * .24, 7, -1.2));
	};
	/** 靴子（HUD「移動」的同一隻，qIcons.js）加兩道速度線：移動過、移動後、移動時共用。 */
	var boot = (c, o) => {
		at$1(c, 2.6, .4, .4, (q) => {
			q.translate(-27, -24);
			Q.ART.hud.move.d(q, o);
		});
		rr(c, CREAM$1, -10.6, -4.4, 4.6, 2.4, 1.2);
		rr(c, CREAM$1, -10.6, 1.4, 3.4, 2.4, 1.2);
	};
	var bootOnly = (c, o) => at$1(c, 0, 0, .47, (q) => {
		q.translate(-27, -24);
		Q.ART.hud.move.d(q, o);
	});
	/** 逆時針的回轉箭頭（反應：卡片小圖、骨架徽章、額外反應共用）。 */
	var react = (c, o, col = "#5ad06a", hi = "#c8f8d0") => {
		st$1(c, col, 4.2, (x) => x.arc(0, .6, 7, -PI$1 * .2, PI$1 * 1.22), "butt");
		if (!o.tiny) st$1(c, hi, 1.4, (x) => x.arc(0, .6, 8, PI$1 * .25, PI$1 * .8), "butt");
		at$1(c, -5.6, -3.6, 1, (q) => poly(q, col, [
			[-5.4, 1.6],
			[5.4, 1.6],
			[0, -5.6]
		], .4), .85);
	};
	var hourglass$1 = (c, _o) => {
		rr(c, "#8ab8f0", -7.8, -10.6, 15.6, 3.4, 1.5);
		rr(c, "#8ab8f0", -7.8, 7.2, 15.6, 3.4, 1.5);
		poly(c, "#e6f4ff", [
			[-6, -7.4],
			[6, -7.4],
			[1.1, 0],
			[6, 7.4],
			[-6, 7.4],
			[-1.1, 0]
		], .4);
		poly(c, "#ffc23a", [
			[-4, -6],
			[4, -6],
			[0, -.8]
		]);
		poly(c, "#e8962a", [
			[-4.6, 7],
			[4.6, 7],
			[0, 3.4]
		]);
	};
	var clock = (c, o) => {
		ci(c, "#8ab8f0", 0, 0, 10.2);
		ci(c, "#f2f8ff", 0, 0, 7.3);
		if (!o.tiny) el(c, "#ffffff", -2.6, -3, 2.6, 1.5, -.6);
		ln(c, "#26365a", 2.1, [
			[0, -4.6],
			[0, 0],
			[3.7, 2.3]
		]);
	};
	var bolt = (c, o) => {
		poly(c, "#ffd23a", [
			[1.6, -10.6],
			[-7.6, 1.6],
			[-1.6, 1.6],
			[-4.2, 10.6],
			[7, -2.6],
			[1, -2.6],
			[4.2, -10.6]
		], .5);
		if (!o.tiny) poly(c, "#fff6b0", [
			[1.8, -9.4],
			[-5.6, .6],
			[-3.4, .6],
			[3.2, -9.4]
		]);
	};
	var crystal = (c) => {
		poly(c, "#b8a8ff", [
			[0, -10.6],
			[7.8, -4.6],
			[7.8, 4.6],
			[0, 10.6],
			[-7.8, 4.6],
			[-7.8, -4.6]
		], .6);
		poly(c, "#f2ecff", [
			[0, -10.6],
			[-7.8, -4.6],
			[0, -1]
		]);
		poly(c, "#d6ccff", [
			[-7.8, -4.6],
			[-7.8, 4.6],
			[0, -1]
		]);
		poly(c, "#7a68c8", [
			[7.8, -4.6],
			[7.8, 4.6],
			[0, 10.6],
			[0, -1]
		]);
		poly(c, "#9a86ff", [
			[-7.8, 4.6],
			[0, 10.6],
			[0, -1]
		]);
	};
	var dice$1 = (c, o) => at$1(c, 0, 0, 1, (q) => {
		rr(q, "#f6f2e6", -8.2, -8.2, 16.4, 16.4, 3.6);
		f(q, "rgba(0,0,0,0.16)", () => q.roundRect(-8.2, 4.6, 16.4, 3.6, [
			0,
			0,
			3.6,
			3.6
		]));
		for (const [x, y] of o.tiny ? [
			[-3.8, -3.8],
			[0, 0],
			[3.8, 3.8]
		] : [
			[-4, -4],
			[4, 4],
			[0, 0],
			[4, -4],
			[-4, 4]
		]) ci(q, INK, x, y, o.tiny ? 2.1 : 1.8);
	}, .2);
	var banner = (c, o) => {
		rr(c, "#9a6ab8", -8.6, -10.6, 17.2, 3.6, 1.6);
		poly(c, LILAC, [
			[-6.6, -8],
			[6.6, -8],
			[6.6, 9.6],
			[0, 4.4],
			[-6.6, 9.6]
		], .8);
		f(c, "#eed8f6", () => c.rect(-6.6, -7, 3, 13));
		if (!o.tiny) star4(c, "#ffffff", 1.2, -1.4, 4.4, null);
	};
	var tag = (c, o) => at$1(c, 0, 0, .9, (q) => {
		poly(q, GOLD$1, [
			[-9.6, 0],
			[-3.4, -7.4],
			[9.6, -7.4],
			[9.6, 7.4],
			[-3.4, 7.4]
		], 1);
		f(q, "#fff0b0", () => q.rect(-2.6, -7.4, 12.2, 3));
		ci(q, "#5a3a06", -4.4, 0, 2.1);
		if (!o.tiny) {
			f(q, "#9c7420", () => q.rect(0, -.6, 7, 1.8));
			f(q, "#9c7420", () => q.rect(0, 3, 5, 1.8));
		}
	}, -.5);
	var wall = (c, x = 5.4) => {
		rr(c, STONE$1, x, -10.4, 5, 20.8, 1.4);
		f(c, STONE_L$1, () => c.rect(x, -9.4, 1.8, 18.8));
	};
	var puddle = (c, col = "#4aa8ff", hi = "#cfe8ff", y = 7) => {
		el(c, col, 0, y, 10.6, 3.6);
		el(c, hi, -2.6, y - .8, 5, 1.2);
	};
	var tablet = (c, _o) => {
		f(c, "#9a9282", () => c.roundRect(-7.6, -10.4, 15.2, 20.8, [
			6.4,
			6.4,
			1.8,
			1.8
		]));
		f(c, "#cfc8b6", () => c.roundRect(-7.6, -10.4, 3.8, 20.8, [
			6.4,
			0,
			0,
			1.8
		]));
		poly(c, "#ffd23f", [
			[0, -6.2],
			[5, .4],
			[0, 7],
			[-5, .4]
		], .4);
		poly(c, "#fff6c8", [
			[0, -2.6],
			[2.4, .4],
			[0, 3.4],
			[-2.4, .4]
		]);
	};
	var paw = (c, o, col = "#c9a0ff", hi = "#ecdcff") => {
		el(c, col, 0, 4, 6.4, 5.2);
		for (const [x, y, r] of [
			[
				-7,
				-1.8,
				2.7
			],
			[
				-2.6,
				-6.8,
				3
			],
			[
				2.6,
				-6.8,
				3
			],
			[
				7,
				-1.8,
				2.7
			]
		]) ci(c, col, x, y, r);
		if (!o.tiny) el(c, hi, -2, 2.4, 2.6, 1.5, -.4);
	};
	var shieldBlue = (c, _o, T = ["#6ab8f0", "#cfe8ff"]) => {
		poly(c, T[0], [
			[-9.4, -9.6],
			[9.4, -9.6],
			[8.8, 2],
			[0, 10],
			[-8.8, 2]
		], 1);
		poly(c, T[1], [
			[-9.4, -9.6],
			[0, -9.6],
			[0, 10],
			[-8.8, 2]
		], 1);
	};
	var hood = (c, _o) => {
		f(c, "#8a6ad8", () => {
			c.moveTo(0, -10.6);
			c.bezierCurveTo(8.6, -10.6, 10, -2, 9.6, 10.2);
			c.lineTo(-9.6, 10.2);
			c.bezierCurveTo(-10, -2, -8.6, -10.6, 0, -10.6);
			c.closePath();
		});
		f(c, "#b89af0", () => c.ellipse(-5.6, -3, 2, 6, .25, 0, TAU$3));
		el(c, "#2a1650", 0, .6, 5.8, 5.6);
		poly(c, "#ffe14d", [
			[-4.4, -.8],
			[-.8, .8],
			[-1.2, 2.4],
			[-4, 1.6]
		], .2);
		poly(c, "#ffe14d", [
			[4.4, -.8],
			[.8, .8],
			[1.2, 2.4],
			[4, 1.6]
		], .2);
	};
	var crate = (c, o, x = 0, y = 0, s = 17) => {
		rr(c, "#a06a36", x - s / 2, y - s / 2, s, s, s * .12);
		f(c, "#d8a868", () => c.roundRect(x - s / 2, y - s / 2, s, s * .2, [
			s * .12,
			s * .12,
			0,
			0
		]));
		f(c, "#6a4420", () => c.roundRect(x - s / 2, y + s * .32, s, s * .18, [
			0,
			0,
			s * .12,
			s * .12
		]));
		if (!o.small) ln(c, "#6a4420", s * .09, [[x - s * .3, y - s * .2], [x + s * .3, y + s * .24]]);
	};
	var grid3 = (c, lit = "#ffb23a", mid = "#fff6c8") => {
		c.save();
		c.scale(.8, .8);
		for (let i = 0; i < 9; i++) rr(c, i === 4 ? mid : lit, -10 + i % 3 * 6.9, -10 + Math.floor(i / 3) * 6.9, 6.2, 6.2, 1.4);
		c.restore();
	};
	var qmark = (c, o, x, y, k = 1) => halo(c, o, (q) => {
		st$1(q, "#ffe9a8", 2.4 * k, (p) => {
			p.arc(x, y - 2.6 * k, 2.6 * k, PI$1 * 1.05, PI$1 * .5);
			p.lineTo(x, y + 1.6 * k);
		});
		ci(q, "#ffe9a8", x, y + 4.6 * k, 1.4 * k);
	});
	/** 主圖樣縮到左下、右上角壓一個小圖（修正的「改了什麼」、召喚物數值用）。 */
	var withBadge = (base, small, bk = .8, sk = .48) => (c, o, T, opt) => {
		at$1(c, -2.2, 2.2, bk, (q) => base(q, o));
		halo(c, o, (q) => at$1(q, 6, -5.6, sk, (p) => small(p, {
			...o,
			tiny: true,
			small: true,
			owPx: 0,
			flat: true
		}, T, opt)));
	};
	var upArrow = (c, _o, T = ["#ffb23a", "#fff6c8"]) => {
		poly(c, T[0], [
			[0, -11],
			[10, -1],
			[4, -1],
			[4, 9.6],
			[-4, 9.6],
			[-4, -1],
			[-10, -1]
		], .6);
		poly(c, T[1], [
			[0, -11],
			[-10, -1],
			[-4, -1],
			[-4, 9.6],
			[0, 9.6]
		]);
	};
	var downArrow = (c, o, T = ["#6ae0ff", "#d8f8ff"]) => {
		c.save();
		c.scale(1, -1);
		upArrow(c, o, T);
		c.restore();
	};
	/** 修正內容的小箭頭照數值正負（第 2 版；沒給數值當正）：正＝朝上的橘黃、負＝朝下的青色。 */
	var signArrow = (c, o, opt) => (opt?.value ?? 1) < 0 || opt?.value === false ? downArrow(c, o) : upArrow(c, o);
	/** 亮色單手劍（第 2 版：必修 1）。第 1 批 W.swordArt 的柄是深握柄色、護手是暗金，在深色圓底上整把只剩一條灰褐細線；
	*  這裡照規則 6 換亮一階：刃亮鋼加寬到上限（刃寬 5.8／全長 28.5≈1/5）、護手換金、握柄換皮色（混亮一階 #a8703e）、柄頭金。直立座標：刃尖朝 −y，中心在原點。
	*  B＝刃的三色（本色、亮面、暗面），附魔的劍換刃色。 */
	var BLADE_STEEL = [
		STEEL,
		"#ffffff",
		"#98a2ae"
	];
	var bladeSword = (c, _o, B = BLADE_STEEL) => {
		c.save();
		c.translate(0, -.65);
		poly(c, B[0], [
			[-2.9, 3.6],
			[-2.9, -9.4],
			[0, -13.6],
			[2.9, -9.4],
			[2.9, 3.6]
		], .4);
		poly(c, B[1], [
			[-2.9, 3.6],
			[-2.9, -9.4],
			[0, -13.6],
			[-.4, -9.4],
			[-.4, 3.6]
		]);
		f(c, B[2], () => c.rect(1.3, -9, 1.6, 12.6));
		rr(c, GOLD$1, -6.4, 3.4, 12.8, 3.4, 1.5);
		f(c, "#fff0b0", () => c.roundRect(-6.4, 3.4, 12.8, 1.2, [
			1.5,
			1.5,
			0,
			0
		]));
		rr(c, "#a8703e", -1.7, 6.6, 3.4, 5.4, 1);
		ci(c, GOLD$1, 0, 12.6, 2.4);
		c.restore();
	};
	/** 斜放（刃尖朝右上）的亮劍，k＝縮放。k 0.84 時劍尖、柄頭剛好貼到圓片色環的內緣。 */
	var diagSword = (k = .84, B) => (c, o) => at$1(c, 0, 0, k, (q) => bladeSword(q, o, B), PI$1 / 4);
	/** 亮鋼匕首（第 2 版：必修 1 的背刺）：刃寬 5.6、刃尖朝 +y。 */
	var dagger = (c, _o) => {
		poly(c, STEEL, [
			[-2.8, -3.4],
			[2.8, -3.4],
			[2.8, 2.6],
			[0, 8.6],
			[-2.8, 2.6]
		], .4);
		poly(c, "#ffffff", [
			[-2.8, -3.4],
			[-.3, -3.4],
			[-.3, 8],
			[-2.8, 2.6]
		]);
		rr(c, GOLD$1, -4.8, -5.6, 9.6, 2.8, 1.2);
		rr(c, "#a8703e", -1.5, -10, 3, 4.6, 1);
		ci(c, GOLD$1, 0, -10.4, 1.9);
	};
	/** 雙 V（第 2 版：必修 2 的衝鋒、位移徽章）：兩個朝右的粗 V 拉開，中間留 ≥4 單位（12px 圖樣裡約 2.5 個裝置像素）的底色；後面那個降一階色。 */
	var chevron = (c, x, col, hi) => {
		poly(c, col, [
			[x - 5.4, -9],
			[x - .4, -9],
			[x + 5.4, 0],
			[x - .4, 9],
			[x - 5.4, 9],
			[x + .4, 0]
		], .5);
		if (hi) poly(c, hi, [
			[x - 5.4, -9],
			[x - .4, -9],
			[x + 5.4, 0],
			[x + .4, 0]
		]);
	};
	var dashArt = (c, o) => {
		chevron(c, -5.2, "#b9a57e", o.tiny ? null : "#d8c8a0");
		chevron(c, 5.2, CREAM$1, o.tiny ? null : "#ffffff");
	};
	/** 範圍徽章（第 2 版：必修 4）：九宮格留給形狀，徽章改成「向外擴的衝擊環」——中心一顆黃白的小爆星，外面一圈斷成四段的橘色粗環（斷口在上下左右），環外四個斜角各一道往外的短衝擊線。 */
	var areaBurst = (c, o) => {
		for (let i = 0; i < 4; i++) {
			const a = i * PI$1 / 2;
			st$1(c, "#ffb23a", 3.2, (x) => x.arc(0, 0, 7.4, a + .32, a + PI$1 / 2 - .32), "butt");
			at$1(c, 0, 0, 1, (q) => poly(q, "#ffe08a", [
				[9.4, -1.3],
				[11.6, 0],
				[9.4, 1.3]
			], .6), a + PI$1 / 4);
		}
		poly(c, "#ffd23f", starPts(0, 0, 4.8, 2.4, 6, -PI$1 / 2), .4);
		ci(c, "#ffffff", 0, 0, 1.7);
		if (!o.tiny) st$1(c, "#fff0b0", 1.2, (x) => x.arc(0, 0, 8.4, PI$1 * 1.1, PI$1 * 1.4), "butt");
	};
	/** 中間破口的短厚磚牆（第 2 版：必修 3）：上下兩塊石磚，破口邊緣是鋸齒，旁邊兩顆碎石。 */
	var brokenWall = (c, o) => {
		poly(c, STONE$1, [
			[-4, -10.6],
			[4, -10.6],
			[4, -4.6],
			[2, -3.4],
			[.4, -5],
			[-1.8, -3.2],
			[-4, -4.4]
		], .4);
		poly(c, STONE$1, [
			[-4, 10.6],
			[4, 10.6],
			[4, 4.2],
			[1.8, 3.2],
			[0, 4.8],
			[-2, 3.4],
			[-4, 4.8]
		], .4);
		f(c, STONE_L$1, () => {
			c.rect(-4, -10.6, 8, 1.8);
			c.rect(-4, 4.8, 2, 5.8);
			c.rect(-4, -10.6, 2, 6);
		});
		if (!o.tiny) {
			f(c, STONE_D$1, () => {
				c.rect(-4, -7.2, 8, 1);
				c.rect(-4, 7.6, 8, 1);
			});
			ci(c, STONE_L$1, 7.6, -6.6, 1.3);
			ci(c, STONE_L$1, 8.4, 6.8, 1.1);
		}
	};
	/** 油表面（第 2 版：可修）：第 3 批的「一灘加一滴」染成褐色像一坨醬；圓片裡換成琥珀黃（同一個液體外形），水滴上加白色反光。試過壓扁成一灘不畫那一滴：18px 像麵包、熱狗。 */
	var oilPool = (c, o) => {
		ACT.surface.d(c, o, ["#e8a830", "#fff0b0"], "oil");
		el(c, "#ffffff", -3.7, -3.6, 1.1, 2.2, .4);
		if (!o.tiny) el(c, "#ffffff", 4.6, 5.2, 2, .7);
	};
	/** 靈魂連結的雙環（11-12：效果「分擔傷害」改用；畫法照抄 qIconsStatus.js 的 NEW.soul_link，一筆不改——這個檔比第⑤批先載入，不能呼叫它）。 */
	var soulRings = (c, o) => {
		const ring = (q, x, a0 = 0, a1 = TAU$3) => st$1(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, .4, 5.6, a0, a1), "butt");
		ring(c, -3.8);
		halo(c, o, (q) => {
			ring(q, 3.8);
			if (!o.tiny) st$1(q, "#efe2ff", 1.1, (p) => p.arc(3.8, .4, 5.6, PI$1 * 1.15, PI$1 * 1.55), "butt");
		});
		halo(c, o, (q) => ring(q, -3.8, -.75, .05));
		if (!o.tiny) st$1(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, .4, 5.6, PI$1 * 1.15, PI$1 * 1.55), "butt");
	};
	/** 縮到圓片色環以內（第 2 版：可修「畫出圓片」）：方的、寬的圖樣四角會頂到色環。 */
	var fit$2 = (d, k = .84) => (c, o, T, opt) => at$1(c, 0, 0, k, (q) => d(q, o, T, opt));
	/** 姿態類狀態（第 2 版：補畫）：骨架徽章「姿態」同一個六角臂章外形，底色與中間的紋章換成各姿態的題材。 */
	var hexPts = (R) => [
		0,
		1,
		2,
		3,
		4,
		5
	].map((i) => [Math.cos(i / 6 * TAU$3 - PI$1 / 2) * R, Math.sin(i / 6 * TAU$3 - PI$1 / 2) * R]);
	var stancePlate = (col, hi, emblem) => (c, o) => {
		const P = hexPts(10.6);
		poly(c, col, P, .5);
		poly(c, hi, [
			P[0],
			P[5],
			P[4],
			[-5.6, 3],
			[-5.6, -4.4]
		]);
		halo(c, o, (q) => emblem(q, o));
	};
	var SURF_TINT = {
		fire: "fire",
		water: "water",
		ice: "ice",
		poison: "poison",
		holy: "holy",
		oil: "earth",
		darkness: "shadow",
		smoke: "steel"
	};
	var surface = (id) => (c, o) => {
		const t = SURF_TINT[id] ?? "water";
		ACT.surface.d(c, o, TINT[t] ?? TINT.water, t);
	};
	var spirit = (T) => (c, o) => ACT.summon.d(c, o, T ?? ACT.summon.def);
	var EFFECT$1 = {
		damage: {
			zh: "傷害",
			topic: "白色四芒閃光",
			src: "b3:hit",
			d: act$1("hit")
		},
		heal: {
			zh: "治療",
			topic: "綠色粗十字",
			src: "b3:heal",
			d: act$1("heal")
		},
		shield: {
			zh: "護盾",
			topic: "淡藍小盾（白十字紋）",
			src: "b3:shield",
			d: act$1("shield")
		},
		cleanse: {
			zh: "淨化",
			topic: "一大兩小三顆薄荷綠的亮晶晶",
			d: (c, o) => {
				star4(c, "#9af0d0", -2, 1.6, 9);
				star4(c, "#d8fff0", 6.6, -6.4, 4.2, null);
				if (!o.tiny) star4(c, "#d8fff0", 6.4, 6.6, 3, null);
			}
		},
		push: {
			zh: "推擊",
			topic: "朝右上的黃白粗箭頭",
			src: "b3:push",
			d: act$1("push")
		},
		pull: {
			zh: "拉扯",
			topic: "朝左下的青色粗箭頭、尾端圓鉤",
			src: "b3:pull",
			d: act$1("pull")
		},
		knock_prone: {
			zh: "擊倒",
			topic: "黃色撞擊星壓在地面線上",
			src: "b3:knockdown",
			d: act$1("knockdown")
		},
		shockwave: {
			zh: "震波",
			topic: "地面線上一顆撞擊星，兩側各一道往外的弧",
			d: (c, _o) => {
				rr(c, "#b8862a", -11, 6.4, 22, 4.4, 2);
				burstStar(c, 0, -.6, 6.6);
				for (const s of [-1, 1]) st$1(c, "#ffe9a8", 2.8, (x) => x.arc(0, 1, 10.2, s > 0 ? -PI$1 * .36 : PI$1 * 1.1, s > 0 ? -PI$1 * .1 : PI$1 * 1.36), "round");
			}
		},
		teleport: {
			zh: "傳送",
			topic: "紫色傳送圈（看得到洞），中心一顆白閃光",
			d: (c, _o) => {
				ci(c, "#2a1650", 0, 0, 7.6);
				st$1(c, "#9a6ad8", 4.4, (x) => x.arc(0, 0, 8, 0, TAU$3));
				st$1(c, "#e0c8ff", 1.6, (x) => x.arc(0, 0, 8.8, PI$1 * 1.05, PI$1 * 1.6), "butt");
				star4(c, "#ffffff", 0, 0, 5.6, null);
			}
		},
		dash: {
			zh: "衝鋒",
			topic: "兩個朝右的粗 V 拉開（前米白、後降一階的褐米色）",
			d: dashArt
		},
		charge_through: {
			zh: "直線衝撞",
			topic: "黃色長箭頭從一道短厚磚牆中間的破口穿過去",
			d: (c, o) => {
				brokenWall(c, o);
				halo(c, o, (q) => at$1(q, .4, 0, 1.06, (p) => arrowS(p, "#ffd23f", "#ffffff")));
			}
		},
		shadowstep: {
			zh: "瞬步",
			topic: "米白人形背後繞過來一道紫色弧箭頭",
			d: (c, _o) => {
				bust(c, CREAM$1, 3.4, 2.6, .82);
				st$1(c, "#b48aee", 3.6, (x) => x.arc(2.6, .6, 9, PI$1 * .6, PI$1 * 1.66), "butt");
				at$1(c, 2.6 + Math.cos(PI$1 * 1.66) * 9, .6 + Math.sin(PI$1 * 1.66) * 9, 1, (q) => poly(q, "#b48aee", [
					[-4.8, -1],
					[4.8, -1],
					[0, 5]
				], .4), -1.1);
			}
		},
		leap: {
			zh: "跳躍",
			topic: "一道拱形的跳躍軌跡，落點朝下的箭頭",
			d: (c, _o) => {
				st$1(c, CREAM$1, 3.8, (x) => {
					x.moveTo(-9, 7.6);
					x.quadraticCurveTo(-2, -15.5, 6, 1.6);
				}, "butt");
				poly(c, CREAM$1, [
					[1.4, 1.6],
					[10.8, .4],
					[7.6, 9.6]
				], .5);
				rr(c, "#b8862a", -11, 7.6, 6, 3, 1.5);
			}
		},
		swap: {
			zh: "交換位置（傳送他人、任意兩者互換同圖）",
			topic: "上下兩個反向的箭頭（米白朝右、青色朝左）",
			d: (c, _o) => {
				at$1(c, 0, -5, 1, (q) => arrowS(q, CREAM$1, "#ffffff"));
				at$1(c, 0, 5, 1, (q) => arrowS(q, "#6ae0ff", "#d8f8ff"), PI$1);
			}
		},
		apply_status: {
			zh: "施加狀態（沒指定是哪個狀態時）",
			topic: "掛在橫桿上的淡紫小旗（燕尾）",
			d: banner
		},
		create_surface: {
			zh: "產生表面（沒指定哪種表面時）",
			topic: "一灘水漬上落下一滴",
			src: "b3:surface",
			d: surface("water")
		},
		blow_surface: {
			zh: "吹送",
			topic: "一道捲起來的風，吹著一顆水滴",
			d: (c, _o) => {
				st$1(c, "#7fe0c0", 3.6, (x) => {
					x.moveTo(-10, -2.4);
					x.lineTo(2.6, -2.4);
					x.arc(2.6, -6, 3.6, PI$1 / 2, -PI$1 * .8, true);
				});
				st$1(c, "#dcfff1", 2.8, (x) => {
					x.moveTo(-9, 3.6);
					x.lineTo(-1.6, 3.6);
				});
				at$1(c, 6.4, 4.6, .46, (q) => drop$2(q, "#4aa8ff", 0, 0, 1), -.9);
			}
		},
		enter_form: {
			zh: "進入形態",
			topic: "淡紫色的獸掌印",
			d: (c, o) => paw(c, o)
		},
		leave_form: {
			zh: "解除形態",
			topic: "米白人形，左下一個變暗縮小的掌印",
			d: (c, o) => {
				at$1(c, -6.4, 5.4, .46, (q) => paw(q, { tiny: true }, "#9a7ad0"));
				halo(c, o, (q) => bust(q, CREAM$1, 2.6, 1.2, 1.02));
			}
		},
		clear_surface: {
			zh: "清除表面",
			topic: "一把掃帚（木柄、金色帚頭）",
			d: (c, o) => {
				ln(c, "#a06a36", 2.8, [[8, -9.6], [-1, -1]]);
				poly(c, GOLD$1, [
					[-4.4, -3.4],
					[2.4, 3.4],
					[-3.4, 9.8],
					[-10.4, 2.8]
				], .6);
				poly(c, "#fff0b0", [
					[-4.4, -3.4],
					[-1.6, -.6],
					[-8, 5],
					[-10.4, 2.8]
				]);
				ln(c, "#8a5a32", 2.2, [[-3.6, -2.6], [1.4, 2.4]]);
				if (!o.tiny) star4(c, "#ffffff", 7, 6, 3.6, null);
			}
		},
		destroy_object: {
			zh: "摧毀物件",
			topic: "一個木箱，中間一道裂開的閃電形裂縫",
			d: (c, _o) => {
				crate(c, { small: true }, 0, 0, 18);
				ln(c, OUT, 3.6, [
					[-1.6, -9.4],
					[2, -2.6],
					[-2.4, 1.6],
					[1.4, 9.4]
				], "miter");
				ln(c, "#ffd23f", 1.3, [
					[-1.6, -9.4],
					[2, -2.6],
					[-2.4, 1.6],
					[1.4, 9.4]
				], "miter");
			}
		},
		create_obstacle: {
			zh: "產生障礙",
			topic: "三排交錯的灰石磚牆",
			d: fit$2((c, _o) => {
				for (const [x, y, w] of [
					[
						-10,
						-9.6,
						9.4
					],
					[
						.6,
						-9.6,
						9.4
					],
					[
						-10,
						-3,
						4.6
					],
					[
						-4.2,
						-3,
						8.4
					],
					[
						5.4,
						-3,
						4.6
					],
					[
						-10,
						3.6,
						9.4
					],
					[
						.6,
						3.6,
						9.4
					]
				]) {
					rr(c, STONE$1, x, y, w, 5.6, 1.2);
					f(c, STONE_L$1, () => c.roundRect(x, y, w, 1.8, [
						1.2,
						1.2,
						0,
						0
					]));
				}
			}, .82)
		},
		raise_terrain: {
			zh: "隆起地形",
			topic: "地面裂開、中間頂出一根高高的石柱，柱頂左上一個小黃箭頭",
			d: (c, o) => {
				rr(c, STONE_D$1, -10.8, 6.6, 21.6, 4, 1.6);
				rr(c, STONE$1, -4.6, -8.6, 9.2, 16.4, 1.4);
				f(c, STONE_L$1, () => c.roundRect(-4.6, -8.6, 9.2, 2.6, [
					1.4,
					1.4,
					0,
					0
				]));
				f(c, STONE_L$1, () => c.rect(-4.6, -8.6, 2.4, 16));
				for (const s of [-1, 1]) poly(c, STONE$1, [
					[s * 5.8, 6.6],
					[s * 9.4, 2.6],
					[s * 10.4, 6.6]
				], .3);
				at$1(c, -7.8, -2.4, .4, (q) => upArrow(q, o, ["#ffd23f", "#ffffff"]));
			}
		},
		lower_terrain: {
			zh: "下陷地形",
			topic: "地面中間凹下去一個坑，上面一個朝下的黃箭頭",
			d: (c, o) => {
				poly(c, STONE$1, [
					[-10.4, 2.6],
					[-5.4, 2.6],
					[-3.6, 8],
					[3.6, 8],
					[5.4, 2.6],
					[10.4, 2.6],
					[10.4, 10.4],
					[-10.4, 10.4]
				], .4);
				f(c, STONE_L$1, () => {
					c.rect(-10.6, 2.2, 5.4, 1.8);
					c.rect(5.2, 2.2, 5.4, 1.8);
				});
				at$1(c, 0, -2.8, .6, (q) => {
					q.scale(1, -1);
					upArrow(q, o, ["#ffd23f", "#ffffff"]);
				});
			}
		},
		intercept: {
			zh: "替隊友擋攻擊",
			topic: "米白人形前面擋著一面藍盾",
			d: (c, o) => {
				bust(c, CREAM$1, -3.6, .6, .98);
				halo(c, o, (q) => at$1(q, 4.6, 2.8, .62, (p) => ACT.shield.d(p, o, ACT.shield.def)));
			}
		},
		add_stack: {
			zh: "累積層數",
			topic: "三根越來越高的金色粗條",
			src: "b3:builder",
			d: act$1("builder")
		},
		consume_stack: {
			zh: "消耗層數",
			topic: "兩根金色粗條，第三根的位置炸成一顆橘色爆星",
			d: (c, o) => {
				for (const [x, h] of [[-10.6, 7.6], [-3.4, 12.6]]) {
					rr(c, GOLD$1, x, 9.6 - h, 6.6, h, 1.6);
					f(c, "#fff6c8", () => c.roundRect(x, 9.6 - h, 6.6, 2.8, [
						1.6,
						1.6,
						0,
						0
					]));
				}
				halo(c, o, (q) => at$1(q, 5.6, -3.6, .6, (p) => ACT.detonate.d(p, o, ACT.detonate.def)));
			}
		},
		consume_status: {
			zh: "消耗狀態",
			topic: "橘色十角爆炸、黃白芯",
			src: "b3:detonate",
			d: act$1("detonate")
		},
		place_trap: {
			zh: "放置陷阱",
			topic: "底板上一排朝上的鋼牙",
			src: "b3:trap",
			d: fit$2(act$1("trap"), .8)
		},
		grant_ap: {
			zh: "給予 AP",
			topic: "黃色閃電（和卡片的 AP 同一個）加白色加號",
			d: (c, o) => {
				at$1(c, -1.6, .6, .95, (q) => bolt(q, o));
				plus$1(c, o, 6.6, 6, .86);
			}
		},
		reset_cooldown: {
			zh: "重置冷卻",
			topic: "藍邊白面的鐘，右上角一顆白閃光",
			d: (c, o) => {
				at$1(c, -1.2, 1.2, .9, (q) => clock(q, o));
				halo(c, o, (q) => star4(q, "#ffe14d", 6.6, -6.4, 5, "#ffffff"));
			}
		},
		cheat_death: {
			zh: "免死",
			topic: "紅心，右下一面小藍盾",
			d: (c, o) => {
				at$1(c, -1.2, -1, 1, (q) => heartArt(q, o));
				halo(c, o, (q) => at$1(q, 5.6, 5, .5, (p) => ACT.shield.d(p, o, ACT.shield.def)));
			}
		},
		redirect_damage: {
			zh: "分擔傷害",
			topic: "兩個扣在一起的淡紫圓環（前後交扣；同第⑤批狀態「靈魂連結」）",
			src: "b5:status.soul_link",
			d: soulRings
		},
		copy_skill: {
			zh: "複製技能",
			topic: "兩張疊著的卡（後面紫、前面米白有金星）",
			d: (c, o) => {
				rr(c, "#9a86d8", -9, -10, 11.4, 14.6, 2);
				halo(c, o, (q) => {
					rr(q, CREAM$1, -2.4, -4.6, 11.4, 14.6, 2);
					poly(q, "#e8a020", starPts(3.3, 2.7, 4, 1.7, 5), .2);
				});
			}
		},
		extra_reaction: {
			zh: "額外反應",
			topic: "綠色回轉箭頭（和「反應」同一個）加白色加號",
			d: (c, o) => {
				at$1(c, -1.4, 1.4, .88, (q) => react(q, o));
				plus$1(c, o, 6.8, -6.6, .8);
			}
		},
		hurl_object: {
			zh: "投擲物件",
			topic: "一個木箱沿弧線飛出去",
			d: (c, _o) => {
				st$1(c, CREAM$1, 2.8, (x) => {
					x.moveTo(-9.8, 9);
					x.quadraticCurveTo(-8.6, -2.6, -1.6, -4.4);
				}, "round");
				crate(c, { small: true }, 3.8, -3.4, 12.4);
			}
		},
		topple: {
			zh: "推倒",
			topic: "一根斜倒的石柱，底下地面線",
			d: (c, o) => {
				rr(c, "#b8862a", -11, 6.8, 22, 4, 2);
				at$1(c, -4.6, 6.6, 1, (q) => {
					rr(q, STONE$1, -3.2, -16.4, 6.4, 16.4, 1.2);
					f(q, STONE_L$1, () => q.rect(-3.2, -16, 2.2, 15.6));
					rr(q, STONE_D$1, -4.4, -18, 8.8, 3.2, 1);
				}, .74);
				if (!o.tiny) burstStar(c, 7.6, 3.4, 3.4);
			}
		},
		restore_resource: {
			zh: "回復資源",
			topic: "軟木塞圓底藥瓶，裝著藍色的水",
			d: (c, _o) => {
				rr(c, "#dcecff", -2.4, -9, 4.8, 6, 1);
				rr(c, "#a06a36", -3.2, -11, 6.4, 3, 1);
				ci(c, "#dcecff", 0, 2.6, 8);
				c.save();
				c.beginPath();
				c.rect(-9, -.6, 18, 12);
				c.clip();
				ci(c, "#4a8ae0", 0, 2.6, 6.4);
				c.restore();
				el(c, "#ffffff", -3, 4, 1.3, 2.6, .4);
			}
		},
		steal_buff: {
			zh: "奪取增益",
			topic: "紫色馬蹄形磁鐵（白色兩極）吸著一顆金星",
			d: (c, o) => {
				st$1(c, "#9a6ad8", 5.2, (x) => {
					x.moveTo(-5.6, -1);
					x.lineTo(-5.6, 3.6);
					x.arc(0, 3.6, 5.6, PI$1, 0, true);
					x.lineTo(5.6, -1);
				}, "butt");
				rr(c, "#ffffff", -8.2, -4.6, 5.2, 4, .8);
				rr(c, "#ffffff", 3, -4.6, 5.2, 4, .8);
				halo(c, o, (q) => poly(q, "#ffd23f", starPts(0, -6.6, 4.6, 1.9, 5), .2));
			}
		},
		dispel: {
			zh: "驅散",
			topic: "淡紫的增益箭頭（同「增益」徽章的外形）被一道紅斜槓劃掉",
			d: (c, o) => {
				at$1(c, 0, .4, .92, (q) => ACT.buff.d(q, o, ["#cfc4ff", "#ffffff"]));
				halo(c, o, (q) => {
					if (o.tiny) ln(q, OUT, 5.4, [[-8.6, 8.6], [8.6, -8.6]]);
					ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]);
				});
			}
		},
		reveal: {
			zh: "揭露",
			topic: "一隻睜開的眼睛（米白眼白、藍瞳）",
			d: (c, o) => {
				f(c, CREAM$1, () => {
					c.moveTo(-10.8, 0);
					c.quadraticCurveTo(0, -11, 10.8, 0);
					c.quadraticCurveTo(0, 11, -10.8, 0);
					c.closePath();
				});
				ci(c, "#4aa8ff", 0, 0, 4.8);
				ci(c, "#16223a", 0, 0, 2.3);
				if (!o.tiny) ci(c, "#ffffff", -1.5, -1.6, 1.1);
			}
		},
		revive: {
			zh: "復活",
			topic: "金色的心，兩側一對白翅膀",
			d: fit$2((c, o) => {
				for (const s of [-1, 1]) poly(c, "#fffaf0", [
					[s * 3.6, -3],
					[s * 11, -9],
					[s * 10.6, -2],
					[s * 8.4, 2.4],
					[s * 4, 3.6]
				], .5);
				heart$1(c, "#ffd04a", 0, 1.6, 1.02);
				if (!o.tiny) el(c, "#fff6c8", -2.8, -1.8, 1.8, 1.2, -.6);
			}, .9)
		},
		delayed_damage: {
			zh: "定時炸彈",
			topic: "圓炸彈、彎引信、引信頭一顆火花",
			d: (c, _o) => {
				st$1(c, "#a06a36", 2.2, (x) => {
					x.moveTo(2.6, -5.6);
					x.quadraticCurveTo(4.6, -10, 7.6, -8.6);
				});
				rr(c, "#8a8f99", -.4, -7.2, 5, 3.6, 1);
				ci(c, "#5f6a8c", -1, 2.8, 7.8);
				el(c, "#a8b2d0", -3.8, -.4, 2.8, 1.7, -.6);
				poly(c, "#ffd23f", starPts(8.2, -8.2, 3.6, 1.5, 6), .2);
			}
		},
		summon: {
			zh: "召喚",
			topic: "一隻青色的小靈",
			src: "b3:summon",
			d: spirit()
		},
		zone: {
			zh: "持續區域",
			topic: "地上一圈藍色虛線環，上面浮著一個小沙漏",
			d: (c, o) => {
				for (let i = 0; i < 6; i++) st$1(c, "#8ab8f0", 2.8, (x) => x.ellipse(0, 6.2, 9.6, 3.6, 0, i / 6 * TAU$3 + .18, (i + 1) / 6 * TAU$3 - .18), "butt");
				halo(c, o, (q) => at$1(q, 0, -3.4, .64, (p) => hourglass$1(p, o)));
			}
		},
		rule_change: {
			zh: "規則改變",
			topic: "一張卷軸（上下金色卷軸桿、三行字）",
			d: (c, o) => {
				rr(c, CREAM$1, -6.8, -8.4, 13.6, 16.8, 1.2);
				rr(c, "#d8b04a", -8.8, -10.6, 17.6, 4, 2);
				rr(c, "#d8b04a", -8.8, 6.6, 17.6, 4, 2);
				if (!o.tiny) for (const [y, w] of [
					[-4, 8.4],
					[-.8, 8.4],
					[2.4, 5.4]
				]) f(c, "#8a6a2a", () => c.rect(-4.2, y, w, 1.7));
			}
		},
		gamble: {
			zh: "賭注",
			topic: "一顆斜放的白骰子",
			d: dice$1
		},
		grant_skill: {
			zh: "暫時獲得技能",
			topic: "一張米白的卡（金星）加白色加號",
			d: (c, o) => {
				rr(c, CREAM$1, -8.8, -8.4, 11.6, 16.4, 2);
				poly(c, "#e8a020", starPts(-3, 0, 4, 1.7, 5), .2);
				plus$1(c, o, 6.6, -5.8, .82);
			}
		},
		sacrifice_summon: {
			zh: "獻祭召喚物",
			topic: "小靈背後一圈橘色的爆炸",
			d: fit$2((c, o) => {
				poly(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), .3);
				halo(c, o, (q) => at$1(q, 0, .6, .74, (p) => ACT.summon.d(p, o, ACT.summon.def)));
			}, .9)
		},
		inscribe: {
			zh: "刻印",
			topic: "圓頂的石碑，上面一個金色菱形符文",
			d: tablet
		},
		detonate_runes: {
			zh: "引爆符文",
			topic: "符文石碑背後一圈橘色的爆炸",
			d: fit$2((c, o) => {
				poly(c, "#ff7a2a", starPts(0, 0, 11, 6.6, 10), .3);
				halo(c, o, (q) => at$1(q, 0, .4, .64, (p) => tablet(p, o)));
			}, .9)
		}
	};
	var EFFECT_ALIAS = {
		teleport_target: "swap",
		swap_any: "swap"
	};
	var SURFACE = Object.fromEntries(Object.entries({
		water: "水",
		poison: "毒",
		oil: "油",
		fire: "火焰",
		ice: "冰",
		holy: "聖光",
		darkness: "黑暗",
		smoke: "煙霧"
	}).map(([id, zh]) => [id, {
		zh: zh + "表面",
		topic: {
			fire: "餘燼上三撮火苗",
			ice: "薄冰加兩根冰刺",
			holy: "地上一圈金光加一顆光點",
			darkness: "兩團紫色的霧",
			smoke: "兩團灰白的煙",
			oil: "一灘加一滴（琥珀黃、白色反光）"
		}[id] ?? "一灘水漬上落下一滴（染表面色）",
		src: id === "oil" ? "new" : "b3:surface",
		d: id === "oil" ? oilPool : surface(id)
	}]));
	var S48 = (id) => from48((c, o) => Q.ART.status[id].d(c, o));
	var STATUS$1 = {
		slow: {
			zh: "緩速",
			topic: "一只金殼懷錶",
			src: "b3:slow",
			d: act$1("slow")
		},
		frozen: {
			zh: "冰凍",
			topic: "三根淡藍冰晶",
			src: "style:status.frozen",
			d: S48("frozen")
		},
		root: {
			zh: "定身",
			topic: "鐵球加兩節鎖鏈（腳鐐）",
			d: (c, _o) => {
				for (const [x, y] of [[-3.6, -3], [-7.2, -6.8]]) st$1(c, "#e4e9ef", 2.4, (p) => p.ellipse(x, y, 2.5, 1.7, .8, 0, TAU$3));
				ci(c, "#b4bcc6", 3, 3.4, 7.2);
				el(c, "#f2f5f8", .4, .6, 2.8, 1.7, -.6);
				f(c, "rgba(0,0,0,0.18)", () => {
					c.arc(3, 3.4, 7.2, -.2, 1.8);
					c.closePath();
				});
			}
		},
		stun: {
			zh: "暈眩",
			topic: "頭上繞一圈的暈眩弧，弧上一大一小兩顆黃星",
			d: (c, o) => {
				st$1(c, "#fff0b0", 2.4, (x) => x.ellipse(0, 1.6, 10, 4.4, 0, PI$1 * .05, PI$1 * .95), "round");
				poly(c, "#ffd23f", starPts(-3.4, -2.4, 7.4, 3.2, 5), .5);
				if (!o.tiny) poly(c, "#fff6c8", [
					[-3.4, -9.8],
					[-5.4, -4],
					[-3.4, -2.4]
				]);
				poly(c, "#ffd23f", starPts(6.4, 4.4, 4.2, 1.8, 5), .4);
			}
		},
		silenced: {
			zh: "沉默",
			topic: "紫色對話框，裡面一個深色的叉",
			d: fit$2((c, _o) => {
				poly(c, "#c890ff", [
					[-5.4, 3],
					[-6.8, 10],
					[.6, 3.6]
				], .4);
				rr(c, "#c890ff", -10, -9.4, 20, 13.8, 5);
				f(c, "#e6ccff", () => c.roundRect(-8.4, -8.4, 16.8, 3, 3));
				ln(c, INK, 2.6, [[-4.4, -6], [4.4, 1.6]]);
				ln(c, INK, 2.6, [[4.4, -6], [-4.4, 1.6]]);
			}, .86)
		},
		weaken: {
			zh: "虛弱",
			topic: "鋼灰色朝下的粗箭頭加頂槓",
			src: "b3:curse",
			d: act$1("curse", ["#c3ccd6", "#ffffff"])
		},
		vulnerable: {
			zh: "易傷",
			topic: "一面裂開的紅盾",
			d: fit$2((c, o) => {
				shieldBlue(c, o, ["#e8455a", "#ffb0b8"]);
				ln(c, OUT, 2.6, [
					[1.4, -10.4],
					[-1.8, -3.6],
					[2.2, .6],
					[-.8, 5],
					[.6, 10.4]
				], "miter");
			}, .86)
		},
		feared: {
			zh: "恐懼",
			topic: "風格樣張的恐懼",
			src: "style:status.feared",
			d: S48("feared")
		},
		blinded: {
			zh: "致盲",
			topic: "淡紫的眼睛被一道紅斜槓劃掉",
			d: (c, o) => {
				f(c, "#e6d2ff", () => {
					c.moveTo(-10.8, 0);
					c.quadraticCurveTo(0, -9.6, 10.8, 0);
					c.quadraticCurveTo(0, 9.6, -10.8, 0);
					c.closePath();
				});
				ci(c, "#7a4ec0", 0, 0, 4);
				halo(c, o, (q) => ln(q, "#ff5a6a", 3.4, [[-8, 8.4], [8, -8.4]]));
			}
		},
		taunted: {
			zh: "嘲諷",
			topic: "橘紅色的青筋記號（四道彎角）",
			d: (c, _o) => {
				for (let i = 0; i < 4; i++) {
					c.save();
					c.rotate(i * PI$1 / 2);
					st$1(c, "#ff7a3a", 3.8, (x) => {
						x.moveTo(2.6, 9.4);
						x.quadraticCurveTo(2.6, 2.6, 9.4, 2.6);
					});
					c.restore();
				}
			}
		},
		marked: {
			zh: "被標記",
			topic: "紅色準星",
			src: "b3:mark",
			d: act$1("mark")
		},
		burning: {
			zh: "燃燒",
			topic: "一團火（橘外焰、黃內焰）",
			src: "b3:dot",
			d: act$1("dot", TINT.fire, "fire")
		},
		poison: {
			zh: "中毒",
			topic: "一大顆綠毒滴，右上一顆泡",
			src: "b3:el:poison",
			d: from48((c, o) => ELEMENT$1.poison.d(c, {
				...o,
				small: true
			}))
		},
		bleed: {
			zh: "流血",
			topic: "一大一小兩顆紅血滴",
			src: "b3:dot",
			d: act$1("dot", TINT.blood, "blood")
		},
		prone: {
			zh: "倒地",
			topic: "風格樣張的倒地（躺平的人形加撞擊星）",
			src: "style:status.prone",
			d: S48("prone")
		},
		hasted: {
			zh: "加速",
			topic: "風格樣張的加速（綠色雙箭頭）",
			src: "style:status.hasted",
			d: S48("hasted")
		},
		concealed: {
			zh: "隱蔽",
			topic: "紫色兜帽，裡面兩道發亮的斜眼",
			d: hood
		},
		guarded: {
			zh: "護衛",
			topic: "一面圓木盾（鋼邊、直木板、鋼盾心）",
			d: (c, o) => {
				ci(c, "#c3ccd6", 0, 0, 10.4);
				ci(c, "#b8824a", 0, 0, 8.4);
				f(c, "#d6a46a", () => {
					c.arc(0, 0, 8.4, PI$1 * .5, PI$1 * 1.5);
					c.closePath();
				});
				for (const x of [-3.4, 3.4]) f(c, "#7e5a30", () => c.rect(x - .6, -Math.sqrt(70.56 - x * x), 1.2, 2 * Math.sqrt(70.56 - x * x)));
				ci(c, "#c3ccd6", 0, 0, 3.8);
				ci(c, "#ffffff", -1.2, -1.2, 1.5);
				if (!o.tiny) st$1(c, "#ffffff", 1.2, (x) => x.arc(0, 0, 9.6, PI$1 * 1.05, PI$1 * 1.45), "butt");
			}
		},
		defending: {
			zh: "守護",
			topic: "一面木製鳶形盾（鋼邊、中間一道米白直紋）",
			d: fit$2((c, o) => {
				const P = [
					[-9.4, -10.2],
					[9.4, -10.2],
					[9.4, .6],
					[0, 10.8],
					[-9.4, .6]
				], I = [
					[-7.2, -8.2],
					[7.2, -8.2],
					[7.2, -.2],
					[0, 7.8],
					[-7.2, -.2]
				];
				poly(c, "#c3ccd6", P, 1);
				poly(c, "#b8824a", I, .6);
				poly(c, "#d0a068", [
					[-7.2, -8.2],
					[0, -8.2],
					[0, 7.8],
					[-7.2, -.2]
				], .6);
				f(c, "#e8e0c8", () => c.rect(-1.6, -8.6, 3.2, 15.4));
				if (!o.tiny) {
					f(c, "#ffffff", () => c.rect(-9.4, -10.2, 18.8, 1.4));
					ci(c, "#ffffff", -4.6, -4.6, 1);
					ci(c, "#ffffff", 4.6, -4.6, 1);
				}
			}, .86)
		},
		stoneskin: {
			zh: "石膚",
			topic: "灰石色的人形，身上幾道石板裂紋",
			d: (c, o) => {
				bust(c, STONE$1, 0, 1.6, 1.32);
				f(c, STONE_L$1, () => {
					c.arc(-1.4, -5.6, 2.6, PI$1, PI$1 * 1.6);
					c.lineTo(-1.4, -5.6);
					c.closePath();
				});
				ln(c, "#6e6858", 1.6, [
					[-6.4, 4],
					[-2, 5.4],
					[1.6, 3.4],
					[6, 5.6]
				]);
				ln(c, "#6e6858", 1.6, [[-1.4, -4.6], [1.4, -2.6]]);
				if (!o.tiny) f(c, STONE_L$1, () => c.rect(-6.6, 6, 3.6, 3));
			}
		},
		regenerating: {
			zh: "再生",
			topic: "一株綠色的嫩芽（一莖兩葉）",
			d: (c, o) => {
				ln(c, "#4aa84a", 2.8, [[0, 10.2], [0, -1.6]]);
				for (const s of [-1, 1]) {
					c.save();
					c.translate(0, -1.4);
					c.scale(s, 1);
					f(c, "#6ad86a", () => {
						c.moveTo(0, 0);
						c.bezierCurveTo(1.4, -7.6, 7.4, -9.6, 10.4, -8.4);
						c.bezierCurveTo(9.6, -3, 5.4, 1.6, 0, 0);
						c.closePath();
					});
					if (!o.tiny) f(c, "#c8f8b8", () => {
						c.moveTo(1.6, -2);
						c.bezierCurveTo(3, -5.4, 6, -7, 8.6, -7.6);
						c.lineTo(8, -6.4);
						c.bezierCurveTo(5.4, -5.6, 3.4, -4, 1.6, -2);
						c.closePath();
					});
					c.restore();
				}
				rr(c, "#8a5a32", -6.4, 8, 12.8, 3, 1.4);
			}
		},
		empowered: {
			zh: "激昂",
			topic: "一隻彎起來使力的手臂（膚色、握拳朝上）",
			d: (c, o) => {
				f(c, "#f0c49a", () => {
					c.moveTo(-10.6, 9.4);
					c.lineTo(-10.6, 3);
					c.quadraticCurveTo(-8.6, -1.6, -1.6, .6);
					c.quadraticCurveTo(3.6, -3.4, 1.6, -6.2);
					c.lineTo(6.6, -9);
					c.quadraticCurveTo(10.8, -2, 6.4, 4.6);
					c.quadraticCurveTo(1, 10, -4, 9.4);
					c.closePath();
				});
				ci(c, "#f0c49a", 4.4, -7.6, 4.2);
				el(c, "#ffe8d0", -4.4, -.4, 3, 2, -.3);
				if (!o.tiny) {
					el(c, "#ffe8d0", 3, -9, 1.8, 1.1, -.5);
					ln(c, "#c8885a", 1.2, [[2.6, -6.2], [5.6, -5.4]]);
				}
			}
		},
		overwatch: {
			zh: "監視",
			topic: "一支斜舉的黃銅望遠鏡（鏡口淡藍）",
			d: (c, o) => at$1(c, 0, 0, 1, (q) => {
				rr(q, "#a06a36", -12.4, -2.4, 7.4, 4.8, 1.2);
				rr(q, "#e8bb48", -6, -3.2, 8.6, 6.4, 1.4);
				rr(q, "#f6d878", 1.6, -4.2, 9.4, 8.4, 1.6);
				f(q, "#fff6c8", () => {
					q.rect(-6, -3.2, 8.6, 1.6);
					q.rect(1.6, -4.2, 9.4, 1.8);
				});
				rr(q, "#9c7420", 1.2, -4.4, 1.6, 8.8, .6);
				el(q, "#8fe3ff", 11.2, 0, 1.8, 3.8);
				if (!o.tiny) el(q, "#ffffff", 11.4, -1.4, .8, 1.4);
			}, -PI$1 / 4)
		},
		infused_fire: {
			zh: "火焰附魔",
			topic: "刃換成火焰色的斜劍，劍尖一撮火",
			d: (c, o) => {
				diagSword(.8, [
					"#ff8a2a",
					"#ffd23f",
					"#d8501a"
				])(c, o);
				halo(c, o, (q) => flame$1(q, "#ffd23f", 6.4, -6.6, .34));
			}
		},
		infused_holy: {
			zh: "神聖附魔",
			topic: "刃換成金色的斜劍，劍尖一顆白色四芒光",
			d: (c, o) => {
				diagSword(.8, [
					"#ffd75e",
					"#fff6c8",
					"#d8a830"
				])(c, o);
				halo(c, o, (q) => star4(q, "#ffffff", 6.2, -6.2, 4.6, null));
			}
		},
		shielded_charged: {
			zh: "帶電護盾",
			topic: "淡藍小盾（同「護盾」），盾面一道黃閃電（取代白十字）",
			d: fit$2((c, o) => {
				shieldBlue(c, o);
				halo(c, o, (q) => at$1(q, 0, -.2, .72, (p) => bolt(p, o)));
			}, .86)
		},
		stance_guard: {
			zh: "堅守姿態",
			topic: "藍色六角臂章（姿態的外形），中間一面白盾",
			d: stancePlate("#5a86d8", "#9ab8f0", (c, o) => at$1(c, 0, .4, .5, (q) => shieldBlue(q, o, ["#e8eef6", "#ffffff"])))
		},
		stance_bulwark: {
			zh: "堅壁姿態",
			topic: "沙岩色六角臂章，中間一面亮色磚牆（深色磚縫）",
			d: stancePlate("#c89a5a", "#ecc890", (c) => {
				rr(c, "#5e3b1f", -6.6, -5.8, 13.2, 11.6, 1);
				for (const [x, y, w] of [
					[
						-6,
						-5.2,
						5.4
					],
					[
						.6,
						-5.2,
						5.4
					],
					[
						-6,
						-.6,
						2.8
					],
					[
						-2.4,
						-.6,
						4.8
					],
					[
						3.2,
						-.6,
						2.8
					],
					[
						-6,
						4,
						5.4
					],
					[
						.6,
						4,
						5.4
					]
				]) rr(c, "#f2dcb0", x, y, w, 3.6, .6);
			})
		},
		stance_ironwall: {
			zh: "鐵壁姿態",
			topic: "深鋼灰六角臂章，中間三根亮色直鐵條",
			d: stancePlate("#7d8794", "#aab4c0", (c, o) => {
				for (const x of [
					-4.6,
					0,
					4.6
				]) {
					rr(c, "#eef2f6", x - 1.5, -7, 3, 14, 1.2);
					if (!o.tiny) f(c, "#ffffff", () => c.rect(x - 1.5, -7, 1, 14));
				}
				if (!o.tiny) for (const [x, y] of [
					[-7.6, -2.6],
					[7.6, -2.6],
					[-7.6, 2.6],
					[7.6, 2.6]
				]) ci(c, "#3a4048", x, y, .9);
			})
		},
		stance_fury: {
			zh: "狂怒姿態",
			topic: "紅色六角臂章，中間一團黃火",
			d: stancePlate("#e04a3a", "#ff9a8a", (c) => {
				flame$1(c, "#ffd23f", 0, .6, .66);
				flame$1(c, "#ffffff", 0, 3.4, .3);
			})
		},
		stance_holy_1: {
			zh: "聖輝架勢·壹",
			topic: "金色六角臂章，中間一顆白色四芒光",
			d: stancePlate("#e0a830", "#ffe08a", (c) => star4(c, "#ffffff", 0, .4, 7.4, "#fff6c8"))
		},
		stance_shadow_1: {
			zh: "暗影架勢·壹",
			topic: "紫色六角臂章，中間一彎淡紫月牙",
			d: stancePlate("#8a5ac8", "#b89af0", (c) => f(c, "#f0e4ff", () => {
				c.arc(-.6, .4, 6.4, .6, 5.7, false);
				c.arc(2.2, -.8, 5, 4.9, 1.2, true);
				c.closePath();
			}))
		}
	};
	var halfHeart = (c, _o, s = 1.25) => {
		heart$1(c, "#7a2a3a", 0, 1.4, s);
		c.save();
		c.beginPath();
		c.rect(-12, 1, 24, 12);
		c.clip();
		heart$1(c, "#ff5a4a", 0, 1.4, s);
		c.restore();
		st$1(c, "#ff9a8a", 1.5, (x) => {
			x.moveTo(-8.4 * (s / 1.25), 1);
			x.lineTo(8.4 * (s / 1.25), 1);
		}, "butt");
	};
	var COND = {
		height_advantage: {
			zh: "居高臨下",
			topic: "一座山，山頂一個米白小人頭，右上一個朝上的黃箭頭",
			d: (c, o) => {
				poly(c, STONE$1, [
					[-10.6, 9.8],
					[-2.4, -3.6],
					[2.4, 2.6],
					[5, -.6],
					[10.6, 9.8]
				], .6);
				f(c, STONE_L$1, () => {
					c.moveTo(-10.6, 9.8);
					c.lineTo(-2.4, -3.6);
					c.lineTo(-3.4, 9.8);
					c.closePath();
				});
				poly(c, "#f6f2e6", [
					[-2.4, -3.8],
					[.4, 0],
					[-2, 1.4],
					[-4.8, .4]
				], .3);
				ci(c, CREAM$1, -2.4, -7.6, 2.7);
				if (!o.tiny) poly(c, "#ffd23f", [
					[6.6, -10.6],
					[10.8, -5.4],
					[2.4, -5.4]
				], .3);
			}
		},
		target_hp_below: {
			zh: "目標血量低於",
			topic: "一顆心，上半暗紅、下半亮紅",
			d: (c, o) => halfHeart(c, o)
		},
		self_hp_below: {
			zh: "自身血量低於",
			topic: "半滿的心，右下一個米白小人形",
			d: (c, o) => {
				at$1(c, -2.4, -1.6, .86, (q) => halfHeart(q, o));
				halo(c, o, (q) => bust(q, CREAM$1, 5.6, 4.6, .62));
			}
		},
		target_has_status: {
			zh: "目標帶有狀態（沒指定狀態時）",
			topic: "淡紫小旗，右上一個問號",
			d: (c, o) => {
				at$1(c, -2, 1, .9, (q) => banner(q, o));
				qmark(c, o, 7, -5.6, .9);
			}
		},
		target_on_surface: {
			zh: "目標站在表面上",
			topic: "一灘藍水漬上站著米白人形",
			d: (c, o) => {
				puddle(c);
				halo(c, o, (q) => bust(q, CREAM$1, 0, -.8, .96));
			}
		},
		from_behind: {
			zh: "背刺",
			topic: "米白人形，左上一把亮鋼匕首（金護手、皮柄）刺向背後",
			d: (c, o) => {
				bust(c, CREAM$1, 5.2, 3.6, .84);
				halo(c, o, (q) => {
					if (o.tiny) at$1(q, -.4, -.4, .75, (p) => poly(p, OUT, [
						[-5, -4.6],
						[5, -4.6],
						[5, 3.2],
						[0, 11.6],
						[-5, 3.2]
					], .6), -PI$1 / 4);
					at$1(q, -.4, -.4, .75, (p) => dagger(p, o), -PI$1 / 4);
				});
			}
		},
		flanked: {
			zh: "夾擊",
			topic: "中間米白人形，左右各一個朝內的紅色三角",
			d: (c, _o) => {
				bust(c, CREAM$1, 0, .8, .8);
				for (const s of [-1, 1]) poly(c, ENEMY, [
					[s * 10.8, -4.6],
					[s * 5.6, .6],
					[s * 10.8, 5.8]
				], .5);
			}
		},
		target_isolated: {
			zh: "目標落單",
			topic: "一道從上面打下來的光柱，底下一個米白人形",
			d: (c, o) => {
				f(c, "rgba(255,236,170,0.72)", () => {
					c.moveTo(-2.8, -10.8);
					c.lineTo(2.8, -10.8);
					c.lineTo(9.8, 8);
					c.lineTo(-9.8, 8);
					c.closePath();
				});
				el(c, "#ffe9a8", 0, 8, 9.8, 2.6);
				halo(c, o, (q) => bust(q, CREAM$1, 0, 1.6, .8));
			}
		},
		moved_this_turn: {
			zh: "本回合移動過",
			topic: "一隻褐色的靴子，後面兩道速度線",
			src: "style:hud.move",
			d: boot
		},
		first_round: {
			zh: "第一輪",
			topic: "一個金色的粗體數字 1",
			d: (c, _o) => {
				poly(c, "#ffd23f", [
					[-1.6, -10.2],
					[3.2, -10.2],
					[3.2, 6],
					[6.8, 6],
					[6.8, 10.2],
					[-6.2, 10.2],
					[-6.2, 6],
					[-1.6, 6],
					[-1.6, -4.4],
					[-5.8, -2.4],
					[-5.8, -6.8]
				], .5);
				f(c, "#fff6c8", () => c.rect(-1.6, -10.2, 1.8, 16));
			}
		},
		cast_tag_this_turn: {
			zh: "本回合施放過同類技能",
			topic: "一張斜放的金色吊牌（有孔）",
			d: fit$2(tag, .88)
		},
		self_concealed: {
			zh: "潛行偷襲",
			topic: "紫色兜帽，裡面兩道發亮的斜眼",
			d: hood
		},
		on_own_rune: {
			zh: "目標站在自己的符文上",
			topic: "符文石碑，右下一個米白小人形",
			d: (c, o) => {
				at$1(c, -2.6, -.6, .86, (q) => tablet(q, o));
				halo(c, o, (q) => bust(q, CREAM$1, 5.4, 4.6, .62));
			}
		},
		adjacent_ally: {
			zh: "身旁有友方",
			topic: "並排兩個人形（米白與綠）",
			d: (c, o) => {
				bust(c, CREAM$1, -4.6, 1, .84);
				halo(c, o, (q) => bust(q, ALLY, 4.6, 1, .84));
			}
		},
		target_collided: {
			zh: "目標本回合受過撞擊",
			topic: "米白人形撞在右邊一道石牆上，中間一顆撞擊星",
			d: (c, o) => {
				wall(c, 5.6);
				bust(c, CREAM$1, -3, 1.2, .86);
				halo(c, o, (q) => burstStar(q, 3.6, -4.6, 4.8));
			}
		},
		wielding_weapon: {
			zh: "手持指定武器",
			topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄）",
			d: diagSword()
		},
		in_form: {
			zh: "在形態中",
			topic: "三道淡紫色的爪痕",
			d: (c, _o) => at$1(c, 0, 0, 1, (q) => {
				for (const i of [
					-1,
					0,
					1
				]) poly(q, i === 0 ? "#e6d2ff" : "#c9a0ff", [
					[i * 6.4 - 2.2, -10],
					[i * 6.4 + 1.6, -10],
					[i * 6.4 + 2.8, 2],
					[i * 6.4 + .2, 10.2],
					[i * 6.4 - 1.8, 2]
				], .3);
			}, .28)
		}
	};
	var COST = {
		source: {
			zh: "源力",
			topic: "六角的淡紫晶石",
			d: crystal
		},
		gamble: {
			zh: "賭注",
			topic: "一顆斜放的白骰子",
			d: dice$1
		},
		self: {
			zh: "自身代價（失手自傷等）",
			topic: "一顆裂開的紅心",
			d: (c, o) => {
				heartArt(c, o);
				ln(c, OUT, 2.6, [
					[.8, -4.6],
					[-2.2, -.6],
					[2, 2.4],
					[-.6, 5.6],
					[.2, 10]
				], "miter");
			}
		},
		stacks: {
			zh: "消耗層數",
			topic: "兩根金條加一顆橘色爆星",
			d: (c, o) => EFFECT$1.consume_stack.d(c, o)
		},
		once: {
			zh: "每場一次",
			topic: "一張米白票券（兩側缺口），上面一個深色的 1",
			d: (c, _o) => {
				c.scale(.86, .86);
				rr(c, CREAM$1, -10.4, -6.8, 20.8, 13.6, 2.2);
				f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [
					2.2,
					2.2,
					0,
					0
				]));
				ci(c, OUT, -10.6, 0, 2.3);
				ci(c, OUT, 10.6, 0, 2.3);
				poly(c, "#2a1c14", [
					[-.6, -4.6],
					[2, -4.6],
					[2, 4.6],
					[-1.2, 4.6],
					[-1.2, -1.4],
					[-3.2, -.6],
					[-3.2, -3.2]
				], .2);
			}
		},
		delay: {
			zh: "延遲",
			topic: "沙漏（藍框、白玻璃、金沙）",
			d: hourglass$1
		}
	};
	var redStar = (c, x, y, R = 5.4) => {
		poly(c, "#ff4a5a", starPts(x, y, R, R * .45, 6), .3);
		poly(c, "#ffffff", starPts(x, y, R * .5, R * .22, 6));
	};
	var shieldAt = (c, o) => at$1(c, 4.6, 4.6, .56, (q) => ACT.shield.d(q, o, ACT.shield.def));
	var TRIG$1 = {
		on_hit: {
			zh: "命中時",
			topic: "右上一顆大的黃色撞擊閃光，左下短粗的亮劍刺進去",
			d: fit$2((c, o) => {
				at$1(c, -2.2, 2.2, .6, (q) => bladeSword(q, o), PI$1 / 4);
				halo(c, o, (q) => burstStar(q, 3.4, -3.4, 7.6, "#ffd23f"));
			}, .9)
		},
		on_kill: {
			zh: "擊倒時",
			topic: "骷髏頭、紅眼",
			src: "b3:finisher",
			d: fit$2(act$1("finisher"), .88)
		},
		on_crit: {
			zh: "暴擊時",
			topic: "橘黃兩層的八芒大閃光、白芯",
			d: (c, _o) => {
				poly(c, "#ff9a2a", starPts(0, 0, 11, 4.2, 4), .3);
				poly(c, "#ffd23f", starPts(0, 0, 8.2, 3.2, 4, -PI$1 / 4), .3);
				poly(c, "#ffffff", starPts(0, 0, 5, 1.9, 4));
			}
		},
		on_natural_20: {
			zh: "擲出自然 20 時",
			topic: "淡紫的二十面骰（六角、三個切面），正面寫 20",
			d: (c, o) => {
				poly(c, "#cfc4ff", [
					0,
					1,
					2,
					3,
					4,
					5
				].map((i) => [Math.cos(i / 6 * TAU$3 - PI$1 / 2) * 10.6, Math.sin(i / 6 * TAU$3 - PI$1 / 2) * 10.6]), .5);
				poly(c, "#8a76d8", [
					[9.2, -5.3],
					[9.2, 5.3],
					[0, 10.6],
					[5.6, 4]
				]);
				poly(c, "#8a76d8", [
					[-9.2, 5.3],
					[0, 10.6],
					[-5.6, 4]
				]);
				poly(c, "#ffffff", [
					[0, -6.2],
					[5.8, 4],
					[-5.8, 4]
				], .4);
				if (!o.tiny) {
					c.fillStyle = "#3a2a7a";
					c.font = "900 6.2px Arial, sans-serif";
					c.textAlign = "center";
					c.textBaseline = "middle";
					c.fillText("20", 0, 1.2);
				}
			}
		},
		on_move: {
			zh: "移動後",
			topic: "一隻褐色的靴子，後面兩道速度線",
			src: "style:hud.move",
			d: boot
		},
		on_damaged: {
			zh: "受傷時",
			topic: "米白人形，右上一顆紅色撞擊星",
			d: (c, o) => {
				bust(c, CREAM$1, -1.8, 1.4, 1);
				halo(c, o, (q) => redStar(q, 5, -4.8, 5.6));
			}
		},
		on_status_applied: {
			zh: "施加狀態後",
			topic: "掛在橫桿上的淡紫小旗",
			d: banner
		},
		on_cast_tag: {
			zh: "施放帶標籤的技能後",
			topic: "一張斜放的金色吊牌",
			d: fit$2(tag, .88)
		},
		on_collision: {
			zh: "造成撞擊後",
			topic: "一個米白的三角撞上右邊的石牆，中間一顆撞擊星",
			d: (c, o) => {
				wall(c, 5.4);
				poly(c, CREAM$1, [
					[-10.6, -4],
					[-3.6, 0],
					[-10.6, 4]
				], .5);
				halo(c, o, (q) => burstStar(q, 2.6, 0, 6));
			}
		},
		on_turn_start: {
			zh: "回合開始時",
			topic: "藍色地平線上升起半個太陽，五道短光芒",
			d: (c, _o) => {
				for (const a of [
					-1.2,
					-.6,
					0,
					.6,
					1.2
				]) at$1(c, 0, 5, 1, (q) => rr(q, "#ffd23f", -1.3, -12.6, 2.6, 3.8, 1.2), a);
				f(c, "#ffb23a", () => {
					c.arc(0, 5, 7.4, PI$1, 0);
					c.closePath();
				});
				f(c, "#ffe14d", () => {
					c.arc(0, 5, 5.4, PI$1, 0);
					c.closePath();
				});
				rr(c, "#7ab8f0", -10.4, 5, 20.8, 2.8, 1.4);
			}
		},
		on_turn_end: {
			zh: "回合結束時",
			topic: "地平線上一彎淡紫的月牙",
			d: (c, o) => {
				f(c, "#d8c0ff", () => {
					c.arc(-.6, -2.4, 8.2, .2417, 4.652, false);
					c.arc(2.4, -4.9, 6.6, -2.137, .747, true);
					c.closePath();
				});
				rr(c, "#7a5ac8", -11, 6.2, 22, 3.8, 1.9);
				if (!o.tiny) star4(c, "#ffffff", 6.6, -6.6, 2.8, null);
			}
		},
		on_enter_surface: {
			zh: "敵人進入你的表面時",
			topic: "一隻靴子踩進一灘藍水漬",
			d: (c, o) => {
				puddle(c, "#4aa8ff", "#cfe8ff", 7.2);
				halo(c, o, (q) => at$1(q, .6, -2, .82, (p) => bootOnly(p, o)));
			}
		},
		on_summon_downed: {
			zh: "召喚物倒下時",
			topic: "一隻歪倒、變灰的小靈，右下一個朝下的紅箭頭",
			d: (c, o) => {
				at$1(c, -1.8, -1.2, .86, (q) => ACT.summon.d(q, o, ["#8ab0a8", "#d6e6e2"]), .5);
				halo(c, o, (q) => poly(q, ENEMY, [
					[6, 10.6],
					[10.8, 4.6],
					[8, 4.6],
					[8, -1],
					[4, -1],
					[4, 4.6],
					[1.2, 4.6]
				], .3));
			}
		},
		every_n_hits: {
			zh: "每命中 n 次",
			topic: "由小到大斜排的三顆四芒閃光，最後一顆是金色",
			d: (c, o) => {
				star4(c, "#ffffff", -6.8, 4.6, 4.6, null);
				star4(c, "#ffffff", -.6, .6, 5.2, null);
				halo(c, o, (q) => star4(q, "#ffc23a", 5.6, -4.6, 6.4, "#ffffff"));
			}
		},
		enemy_enters_adjacent: {
			zh: "敵人靠近時",
			topic: "右邊米白人形，左邊一個朝它的紅箭頭",
			d: (c, _o) => {
				bust(c, CREAM$1, 5, 1.2, .84);
				at$1(c, -5.6, 1.6, .56, (q) => arrowS(q, ENEMY, "#ffb0a8"));
			}
		},
		enemy_leaves_adjacent: {
			zh: "敵人離開時",
			topic: "左邊米白人形，右邊一個往外的紅箭頭",
			d: (c, o) => {
				bust(c, CREAM$1, -5, 1.2, .84);
				at$1(c, 5.6, 1.6, .56, (q) => arrowS(q, ENEMY, "#ffb0a8"));
				if (!o.tiny) {
					rr(c, ENEMY, -.6, -4.4, 2.4, 2, 1);
					rr(c, ENEMY, -.6, 5.6, 2.4, 2, 1);
				}
			}
		},
		hit_by_spell: {
			zh: "被法術擊中時",
			topic: "左上一顆大的紫色法術星（佔一半），右下一面小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => star4(q, "#c890ff", -3.4, -3.4, 8.6, "#ffffff"));
			}
		},
		hit_by_attack: {
			zh: "被攻擊時",
			topic: "左上一個大的紅箭頭（佔一半）朝右下的小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => at$1(q, -3.2, -3.2, .88, (p) => arrowS(p, ENEMY, "#ffb0a8"), PI$1 / 4));
			}
		},
		hit_by_melee: {
			zh: "被近戰擊中時",
			topic: "左上一把大的亮劍（佔一半）砍向右下的小藍盾",
			d: (c, o) => {
				shieldAt(c, o);
				halo(c, o, (q) => at$1(q, -1.8, -1.8, .58, (p) => bladeSword(p, o), PI$1 * .75));
			}
		},
		ally_targeted: {
			zh: "隊友被瞄準時",
			topic: "綠色人形，外面一圈紅色準星",
			d: (c, _o) => {
				bust(c, ALLY, 0, 1.2, .86);
				for (let i = 0; i < 4; i++) st$1(c, "#ff4a5a", 2.8, (x) => x.arc(0, 0, 9.4, i * PI$1 / 2 + .3, (i + 1) * PI$1 / 2 - .3), "butt");
			}
		},
		ally_downed: {
			zh: "隊友倒下時",
			topic: "躺平的綠色人形，上面一顆小骷髏",
			d: (c, o) => {
				rr(c, ALLY, -10, 3, 13.6, 6, 3);
				ci(c, ALLY, 6.6, 5.6, 3.8);
				rr(c, "#3f7a5a", -10.6, 9, 21.2, 1.8, .9);
				halo(c, o, (q) => at$1(q, -1.6, -4.4, .56, (p) => ACT.finisher.d(p, {
					...o,
					small: true
				}, void 0)));
			}
		},
		ally_hit_adjacent: {
			zh: "身旁隊友受擊時",
			topic: "綠色人形，右上一顆紅色撞擊星",
			d: (c, o) => {
				bust(c, ALLY, -3.4, 1.4, .92);
				halo(c, o, (q) => redStar(q, 5.2, -4.6, 5.4));
			}
		}
	};
	/** 名詞表（glossary）有、現行沒有專屬圖的 5 個觸發（現行畫「?」）：建議各用哪一個。不算在 22 個裡。 */
	var TRIG_ALIAS = {
		targeted_by_melee: "hit_by_melee",
		targeted_by_attack: "hit_by_attack",
		enemy_moves_in_range: "enemy_enters_adjacent",
		ally_hit_in_range: "ally_hit_adjacent",
		kin_hit_in_range: "ally_hit_adjacent"
	};
	var LINK$1 = {
		after_action: {
			zh: "接著做",
			topic: "一個朝右的米白粗箭頭",
			d: (c, _o) => {
				poly(c, CREAM$1, [
					[-10.5, -3.6],
					[-.5, -3.6],
					[-.5, -9.6],
					[10.5, 0],
					[-.5, 9.6],
					[-.5, 3.6],
					[-10.5, 3.6]
				], .5);
				poly(c, "#ffffff", [
					[-10.5, -3.6],
					[-.5, -3.6],
					[-.5, -9.6],
					[10.5, 0],
					[-10.5, 0]
				]);
			}
		},
		on_hit: {
			zh: "命中才觸發",
			topic: "一個綠色的粗勾",
			d: (c, o) => {
				ln(c, "#5ad06a", 4.8, [
					[-8.4, .8],
					[-2.8, 6.4],
					[8.4, -6.4]
				]);
				if (!o.tiny) ln(c, "#d8ffe0", 1.4, [[-7.4, -.4], [-3.6, 3.4]]);
			}
		},
		on_kill: {
			zh: "擊殺才觸發",
			topic: "骷髏頭、紅眼",
			src: "b3:finisher",
			d: fit$2(act$1("finisher"), .88)
		},
		delayed: {
			zh: "延遲觸發",
			topic: "沙漏",
			d: hourglass$1
		},
		after_move: {
			zh: "移動後觸發",
			topic: "靴子加速度線",
			src: "style:hud.move",
			d: boot
		},
		after_gather: {
			zh: "聚集後觸發",
			topic: "左右兩個朝中間的米白大三角，中間一顆金色四芒星",
			d: (c, _o) => {
				for (const s of [-1, 1]) {
					poly(c, CREAM$1, [
						[s * 10.6, -6.4],
						[s * 4.2, 0],
						[s * 10.6, 6.4]
					], .5);
					poly(c, "#ffffff", [
						[s * 10.6, -6.4],
						[s * 4.2, 0],
						[s * 10.6, 0]
					]);
				}
				star4(c, "#ffd23f", 0, 0, 4.6, "#ffffff");
			}
		}
	};
	var SKELETON = {
		strike: {
			zh: "打擊",
			topic: "一把斜放的亮色單手劍（亮鋼寬刃、金護手、皮柄，放大到貼色環）",
			d: diagSword()
		},
		area: {
			zh: "範圍",
			topic: "向外擴的衝擊環：中心黃白小爆星，外面一圈斷成四段的橘色粗環，四個斜角各一道往外的淡黃短衝擊",
			d: areaBurst
		},
		control: {
			zh: "控制",
			topic: "一把金鎖",
			src: "b3:bind",
			d: act$1("bind")
		},
		aura: {
			zh: "增益",
			topic: "朝上的粗箭頭加底槓",
			src: "b3:buff",
			d: act$1("buff")
		},
		summon: {
			zh: "召喚",
			topic: "一隻青色的小靈",
			src: "b3:summon",
			d: spirit()
		},
		trap: {
			zh: "陷阱",
			topic: "底板上一排朝上的鋼牙",
			src: "b3:trap",
			d: fit$2(act$1("trap"), .8)
		},
		displace: {
			zh: "位移",
			topic: "兩個朝右的粗 V 拉開（同效果「衝鋒」）",
			d: dashArt
		},
		rune: {
			zh: "刻印",
			topic: "圓頂石碑加金色菱形符文",
			d: tablet
		},
		consume_status: {
			zh: "引爆狀態",
			topic: "橘色十角爆炸",
			src: "b3:detonate",
			d: act$1("detonate")
		},
		builder_finisher: {
			zh: "累積終結",
			topic: "三根越來越高的金色粗條",
			src: "b3:builder",
			d: act$1("builder")
		},
		stance: {
			zh: "姿態",
			topic: "藍色六角臂章，上面兩道金色 V 形階級條",
			d: (c, _o) => {
				const P = [
					0,
					1,
					2,
					3,
					4,
					5
				].map((i) => [Math.cos(i / 6 * TAU$3 - PI$1 / 2) * 10.6, Math.sin(i / 6 * TAU$3 - PI$1 / 2) * 10.6]);
				poly(c, "#5a86d8", P, .5);
				poly(c, "#9ab8f0", [
					P[0],
					P[5],
					P[4],
					[-5.6, 3],
					[-5.6, -4.4]
				]);
				for (const y of [-2.6, 3.4]) poly(c, "#ffd23f", [
					[-6, y + 1.4],
					[0, y - 3.8],
					[6, y + 1.4],
					[6, y + 4.6],
					[0, y - .6],
					[-6, y + 4.6]
				], .2);
			}
		},
		reaction: {
			zh: "反應",
			topic: "綠色逆時針回轉箭頭",
			d: (c, o) => react(c, o)
		},
		modifier: {
			zh: "改造",
			topic: "一顆金色齒輪",
			src: "b3:modify",
			d: act$1("modify")
		},
		passive: {
			zh: "被動",
			topic: "金色的無限符號（一直生效）",
			d: (c, o) => {
				const P = (x) => {
					x.moveTo(0, 0);
					x.bezierCurveTo(3.6, -8.6, 11, -7, 10, 0);
					x.bezierCurveTo(11, 7, 3.6, 8.6, 0, 0);
					x.bezierCurveTo(-3.6, -8.6, -11, -7, -10, 0);
					x.bezierCurveTo(-11, 7, -3.6, 8.6, 0, 0);
				};
				st$1(c, "#ffc23a", 4, P);
				if (!o.tiny) st$1(c, "#fff6c8", 1.3, (x) => {
					x.moveTo(-9, -1.6);
					x.bezierCurveTo(-8.6, -5.4, -4.6, -5.6, -2.6, -2.6);
				});
			}
		},
		combo: {
			zh: "連段",
			topic: "一大一小兩顆四芒閃光",
			src: "b3:combo",
			d: act$1("combo")
		},
		sacrifice: {
			zh: "獻祭",
			topic: "小靈背後一圈橘色的爆炸",
			d: (c, o) => EFFECT$1.sacrifice_summon.d(c, o)
		}
	};
	var SHAPE_MAP = {
		single: ["單體", "..#/.../@.."],
		self: ["自身", ".../.@./..."],
		ground_tile: ["指定地格", ".v./.#./..."],
		square3: ["3×3", "###/###/###"],
		cross: ["十字", ".#./###/.#."],
		ring: ["環形（自己周圍一圈）", "###/#@#/###"],
		cone: ["錐形", "###/.#./.@."],
		line: ["直線", ".../@##/..."],
		chain: ["連鎖", "#../..#/.#."],
		allies_in_radius: ["範圍內友方", ".a./a@a/.a."],
		unit_then_tile: ["單位再指定格", ".../@>#/..."],
		object_then_tile: ["物件再指定格", ".../o>#/..."],
		unit_pair: ["兩個單位", ".../@=@/..."]
	};
	var UNLIT = "#3a3f4e";
	var LIT = "#ffb23a";
	var shapeArt = (rows) => (c, o) => {
		c.scale(.8, .8);
		rows.split("/").forEach((row, r) => [...row].forEach((ch, i) => {
			const cx = -6.9 + i * 6.9, cy = -6.9 + r * 6.9;
			if (ch === ">") {
				poly(c, "#ffffff", [
					[cx - 2.8, cy - 3.4],
					[cx + 3, cy],
					[cx - 2.8, cy + 3.4]
				], .4);
				return;
			}
			if (ch === "=") {
				poly(c, "#ffffff", [
					[cx - 3.8, cy],
					[cx - 1.2, cy - 2.8],
					[cx - 1.2, cy - .9],
					[cx + 1.2, cy - .9],
					[cx + 1.2, cy - 2.8],
					[cx + 3.8, cy],
					[cx + 1.2, cy + 2.8],
					[cx + 1.2, cy + .9],
					[cx - 1.2, cy + .9],
					[cx - 1.2, cy + 2.8]
				], .2);
				return;
			}
			if (ch === "v") {
				poly(c, "#ffffff", [
					[cx - 3.2, cy - 2.2],
					[cx + 3.2, cy - 2.2],
					[cx, cy + 3]
				], .4);
				return;
			}
			if (ch === "@" || ch === "a") {
				ci(c, ch === "@" ? CREAM$1 : ALLY, cx, cy, 3.5);
				if (!o.tiny) ci(c, "#ffffff", cx - 1.1, cy - 1.1, 1.1);
				return;
			}
			if (ch === "#") {
				rr(c, LIT, cx - 3.25, cy - 3.25, 6.5, 6.5, 1.4);
				if (!o.tiny) f(c, "#ffe0a0", () => c.roundRect(cx - 3.25, cy - 3.25, 6.5, 1.8, [
					1.4,
					1.4,
					0,
					0
				]));
				return;
			}
			if (ch === "o") {
				rr(c, "#c08a4a", cx - 3, cy - 3, 6, 6, 1);
				f(c, "#8a5a2a", () => c.rect(cx - 3, cy + 1.4, 6, 1.6));
				return;
			}
			rr(c, UNLIT, cx - 2.2, cy - 2.2, 4.4, 4.4, 1);
		}));
	};
	var SHAPE = Object.fromEntries(Object.entries(SHAPE_MAP).map(([id, [zh, rows]]) => [id, {
		zh,
		topic: "九宮格示意：" + rows,
		d: shapeArt(rows)
	}]));
	var rangeArt = (c, o) => {
		rr(c, "#ffd23a", -10.4, -3.6, 6.6, 7.2, 1.6);
		poly(c, "#ffffff", [
			[-2.2, -3.4],
			[1.8, 0],
			[-2.2, 3.4]
		], .5);
		rr(c, "#e04a3a", 3.8, -3.6, 6.6, 7.2, 1.6);
		if (!o.tiny) {
			f(c, "#fff3a0", () => c.roundRect(-10.4, -3.6, 6.6, 2, [
				1.6,
				1.6,
				0,
				0
			]));
			f(c, "#ff9a8a", () => c.roundRect(3.8, -3.6, 6.6, 2, [
				1.6,
				1.6,
				0,
				0
			]));
		}
	};
	/** 第 2 版：右上的小箭頭照數值正負（opt.value；正＝朝上橘黃、負＝朝下青色），不再寫死。 */
	var up = (base, bk, sk) => withBadge(base, (c, o, _T, opt) => signArrow(c, o, opt), bk, sk);
	var elementArt = (id) => id === "physical" || !ELEMENT$1[id] ? act$1("hit", [STEEL, "#ffffff"]) : from48((c, o) => ELEMENT$1[id].d(c, {
		...o,
		small: true
	}));
	var CHANGE = {
		add_element: {
			zh: "加上元素",
			topic: "該元素的道具（第 3 批）加白色加號",
			d: (c, o, _T, opt) => {
				at$1(c, -1.6, 1.6, .86, (q) => elementArt(opt?.value ?? "fire")(q, o));
				plus$1(c, o, 6.8, -6.6, .8);
			}
		},
		damage_permille: {
			zh: "傷害增減",
			topic: "白閃光，右上一個小箭頭（照數值正負朝上或朝下）",
			d: up(act$1("hit"))
		},
		hit_bonus: {
			zh: "命中",
			topic: "紅準星，右上一個小箭頭（照正負）",
			d: up(act$1("mark"))
		},
		cooldown_delta: {
			zh: "冷卻",
			topic: "藍鐘，右上一個小箭頭（照正負；冷卻 −1＝朝下青色）",
			d: up(clock)
		},
		area_delta: {
			zh: "範圍",
			topic: "九宮格，右上一個小箭頭（照正負）",
			d: up((c) => grid3(c))
		},
		push_distance_delta: {
			zh: "推距",
			topic: "推開的箭頭，右上一個小箭頭（照正負）",
			d: up(act$1("push"), .74, .44)
		},
		ap_delta: {
			zh: "AP",
			topic: "黃色閃電，右上一個小箭頭（照正負；AP −1＝朝下青色）",
			d: up(bolt)
		},
		range_delta: {
			zh: "射程",
			topic: "黃格、白箭頭、紅格（和卡片的射程同一個），右上一個小箭頭（照正負）",
			d: up(rangeArt)
		},
		add_tags: {
			zh: "加上標籤",
			topic: "金色吊牌加白色加號",
			d: (c, o) => {
				at$1(c, -1.4, 1.4, .86, (q) => tag(q, o));
				plus$1(c, o, 6.8, -6.6, .8);
			}
		},
		on_hit_effects: {
			zh: "命中後效果",
			topic: "那個效果的圖，右上一顆小白閃光",
			d: (c, o, _T, opt) => withBadge(opt?.base ?? act$1("detonate"), (q) => star4(q, "#ffffff", 0, 0, 10.6, null))(c, o)
		},
		shape_to: {
			zh: "形狀改為",
			topic: "新形狀的九宮格示意",
			d: (c, o, T, opt) => (SHAPE[String(opt?.value)] ?? SHAPE.square3).d(c, o, T)
		},
		allow_self_target: {
			zh: "可以對自己用",
			topic: "米白人形，外面一圈綠色的環",
			d: (c, _o) => {
				st$1(c, "#5ad06a", 2.8, (x) => x.arc(0, 0, 9.4, 0, TAU$3));
				bust(c, CREAM$1, 0, 1.2, .84);
			}
		},
		grant_pierce: {
			zh: "穿透",
			topic: "黃箭頭穿過一道石牆",
			d: (c, o) => EFFECT$1.charge_through.d(c, o)
		},
		heal_permille: {
			zh: "治療量",
			topic: "綠十字，右上一個小箭頭（照正負）",
			d: up(act$1("heal"))
		},
		summon_hp_permille: {
			zh: "召喚物 HP",
			topic: "小靈，右上一顆紅心",
			d: withBadge(spirit(), (c, _o) => heart$1(c, "#ff5a4a", 0, 1, 1.3))
		},
		summon_limit_delta: {
			zh: "召喚物上限",
			topic: "小靈，右上一個白色加號（照數值：負＝白色減號）",
			d: (c, o, _T, opt) => {
				at$1(c, -2.2, 2.2, .8, (q) => spirit()(q, o));
				if (Number(opt?.value ?? 1) < 0) minus(c, o, 6.6, -6.4, .8);
				else plus$1(c, o, 6.6, -6.4, .8);
			}
		},
		summon_duration_delta: {
			zh: "召喚物持續",
			topic: "小靈，右上一個小沙漏",
			d: withBadge(spirit(), hourglass$1)
		},
		summon_damage_permille: {
			zh: "召喚物傷害",
			topic: "小靈，右上一顆白閃光",
			d: withBadge(spirit(), (c) => star4(c, "#ffffff", 0, 0, 10.6, null))
		},
		summon_attack_dice: {
			zh: "召喚物攻擊骰",
			topic: "小靈，右上一顆小骰子",
			d: withBadge(spirit(), dice$1)
		},
		form_upkeep_permille: {
			zh: "形態維持消耗",
			topic: "獸掌印、右下壓一個小沙漏，右上一個小箭頭（照正負；−500‰＝朝下青色）",
			d: up((c, o) => {
				paw(c, o);
				halo(c, o, (q) => at$1(q, 6.4, 6.6, .46, (p) => hourglass$1(p, o)));
			})
		},
		form_entry_permille: {
			zh: "形態進入消耗",
			topic: "獸掌印，右上一個小箭頭（照正負）",
			d: up((c, o) => paw(c, o))
		}
	};
	var ELEMENT = Object.fromEntries([
		"physical",
		"fire",
		"ice",
		"lightning",
		"poison",
		"wind",
		"earth",
		"holy",
		"shadow"
	].map((id) => [id, {
		zh: BASE_ZH[id] ?? id,
		topic: id === "physical" ? "鋼白的四芒閃光" : "第 3 批的元素道具：" + ELEMENT$1[id].zh,
		src: id === "physical" ? "b3:hit" : "b3:el:" + id,
		d: elementArt(id)
	}]));
	var hud = (id) => from48((c, o) => Q.ART.hud[id].d(c, o), .46);
	var CARD = {
		ap: {
			zh: "AP",
			topic: "黃色閃電（HUD 的 AP 同一個）",
			src: "style:hud.ap",
			px: 16,
			d: hud("ap")
		},
		mana: {
			zh: "法力",
			topic: "藍色水滴（HUD 的法力同一個）",
			src: "style:hud.mana",
			px: 16,
			d: hud("mana")
		},
		stamina: {
			zh: "耐力",
			topic: "金色的脈搏折線（HUD 的耐力同一個）",
			src: "style:hud.stamina",
			px: 16,
			d: hud("stamina")
		},
		hp: {
			zh: "生命",
			topic: "紅心",
			px: 16,
			d: (c, o) => heartArt(c, o, "#f0503e", "#ffb0a0", 1.3)
		},
		source: {
			zh: "源力",
			topic: "六角的淡紫晶石（和圓片的源力同一個；現行是淡紫五角星）",
			px: 16,
			d: crystal
		},
		uses: {
			zh: "次數",
			topic: "米白票券（兩側缺口、中間一道虛線）",
			px: 16,
			d: (c, _o) => {
				c.scale(.86, .86);
				rr(c, CREAM$1, -10.4, -6.8, 20.8, 13.6, 2.2);
				f(c, "#fffaf0", () => c.roundRect(-10.4, -6.8, 20.8, 3, [
					2.2,
					2.2,
					0,
					0
				]));
				ci(c, OUT, -10.6, 0, 2.3);
				ci(c, OUT, 10.6, 0, 2.3);
				for (const x of [
					-5,
					-1,
					3
				]) f(c, "#8a6a2a", () => c.rect(x, -.9, 2.6, 1.8));
			}
		},
		cooldown: {
			zh: "冷卻",
			topic: "藍邊白面的鐘",
			px: 16,
			d: clock
		},
		range: {
			zh: "射程",
			topic: "黃格（自己）、白箭頭、紅格（目標）",
			px: 16,
			d: rangeArt
		},
		reaction: {
			zh: "反應",
			topic: "綠色逆時針回轉箭頭",
			px: 16,
			d: (c, o) => react(c, o)
		},
		trigger: {
			zh: "觸發",
			topic: "一個橘色的鈴（金色鈴舌）",
			px: 16,
			d: (c, o) => {
				ci(c, "#f0a040", 0, -9.2, 1.8);
				f(c, "#f0a040", () => {
					c.moveTo(-7.8, 5);
					c.quadraticCurveTo(-7, -8.6, 0, -8.6);
					c.quadraticCurveTo(7, -8.6, 7.8, 5);
					c.lineTo(10.2, 7.4);
					c.lineTo(-10.2, 7.4);
					c.closePath();
				});
				ci(c, "#ffd23f", 0, 8.8, 2.3);
				if (!o.tiny) el(c, "#ffe0b0", -3.2, -2.6, 1.5, 4.2, .2);
			}
		},
		delayed: {
			zh: "延遲",
			topic: "沙漏（和圓片的延遲同一個；現行是米白的鐘，和冷卻只差顏色）",
			px: 16,
			d: hourglass$1
		},
		activation: {
			zh: "啟動",
			topic: "金色五角星",
			px: 16,
			d: (c, o) => {
				poly(c, "#ffb938", starPts(0, .6, 10.6, 4.5, 5), .5);
				if (!o.tiny) poly(c, "#fff0b0", [
					[0, -10],
					[-2.6, -2.8],
					[0, .6]
				]);
			}
		},
		drawback: {
			zh: "缺點",
			topic: "琥珀色警告三角，裡面深色驚嘆號",
			px: 16,
			d: (c, _o) => {
				poly(c, "#e0a040", [
					[0, -9.2],
					[9.6, 7.8],
					[-9.6, 7.8]
				], 1.3);
				rr(c, "#2a1c14", -1.4, -4.4, 2.8, 7, 1);
				ci(c, "#2a1c14", 0, 5.4, 1.6);
			}
		},
		damage: {
			zh: "傷害",
			topic: "四芒閃光（染元素色；物理是白）",
			src: "b3:hit",
			px: 18,
			d: (c, o, T) => ACT.hit.d(c, o, T ?? ["#e8eef4", "#ffffff"])
		},
		heal: {
			zh: "治療",
			topic: "綠色粗十字",
			src: "b3:heal",
			px: 18,
			d: act$1("heal")
		},
		shield: {
			zh: "護盾",
			topic: "淡藍小盾",
			src: "b3:shield",
			px: 18,
			d: act$1("shield")
		},
		move: {
			zh: "移動",
			topic: "褐色靴子加速度線",
			src: "style:hud.move",
			px: 18,
			d: boot
		},
		status: {
			zh: "狀態",
			topic: "淡紫小旗",
			px: 18,
			d: banner
		},
		surface: {
			zh: "表面",
			topic: "一灘水漬上落下一滴",
			src: "b3:surface",
			px: 18,
			d: surface("water")
		},
		summon: {
			zh: "召喚",
			topic: "青色小靈",
			src: "b3:summon",
			px: 18,
			d: spirit()
		},
		stack: {
			zh: "層數",
			topic: "三根越來越高的金條",
			src: "b3:builder",
			px: 18,
			d: act$1("builder")
		},
		pin: {
			zh: "圖釘",
			topic: "斜放的圖釘：已釘＝紅頭；未釘（opt.pinned false）＝同外形灰鋼色、55% 不透明",
			px: 13,
			d: (c, _o, _T, opt) => {
				const on = opt?.pinned !== false;
				c.save();
				if (!on) c.globalAlpha = .55;
				at$1(c, 0, 0, 1, (q) => {
					ln(q, on ? STEEL : "#9aa2ac", 2.2, [[0, 2], [0, 10.6]]);
					poly(q, on ? "#c8382e" : "#8a929c", [
						[-3, -5],
						[3, -5],
						[5.8, 2.8],
						[-5.8, 2.8]
					], .6);
					rr(q, on ? "#f05a48" : "#b4bcc6", -5.4, -10.6, 10.8, 5.4, 2.2);
				}, .6);
				c.restore();
			}
		}
	};
	/** 亮色的弓與箭（遠程技能）：木色弓臂往右鼓、白弦、鋼箭頭朝右（現行是一道弧加一支箭）。 */
	var bowArrow = (c, o) => {
		st$1(c, "#d8a868", 3.4, (x) => x.arc(-7, 0, 11, -1.15, 1.15), "round");
		if (!o.tiny) st$1(c, "#fff0d0", 1, (x) => x.arc(-7.6, 0, 11, -.9, -.2), "butt");
		ln(c, "#ffffff", 1.2, [[-2.5, -10], [-2.5, 10]]);
		rr(c, "#c3ccd6", -10.4, -1.3, 15, 2.6, 1);
		poly(c, "#ffffff", [
			[4, -4.4],
			[10.8, 0],
			[4, 4.4]
		], .4);
		poly(c, "#f2e6c8", [
			[-10.8, -4],
			[-6.6, -1.2],
			[-6.6, 1.2],
			[-10.8, 4]
		], .3);
	};
	/** 三張扇開的米白卡（所有技能）：後兩張降一階，前面一張金星。 */
	var cardFan = (c, _o) => {
		for (const [a, col] of [[-.42, "#a8a08a"], [-.14, "#d8ccae"]]) at$1(c, 0, 4, 1, (q) => rr(q, col, -5.4, -14, 10.8, 14.4, 1.8), a);
		at$1(c, 0, 4, 1, (q) => {
			rr(q, CREAM$1, -5.4, -14, 10.8, 14.4, 1.8);
			poly(q, GOLD$1, starPts(0, -6.8, 4, 1.7, 5), .3);
		}, .2);
	};
	var CATS = {
		skeleton: SKELETON,
		effect: EFFECT$1,
		surface: SURFACE,
		status: STATUS$1,
		condition: COND,
		cost: COST,
		trigger: TRIG$1,
		link: LINK$1,
		shape: SHAPE,
		change: CHANGE,
		element: ELEMENT,
		card: CARD,
		target: {
			all_skills: {
				zh: "所有技能",
				topic: "三張扇開的米白卡（前面一張金星）",
				d: cardFan
			},
			all_attacks: {
				zh: "所有攻擊",
				topic: "兩把交叉的亮色劍（打擊徽章那把，成對）",
				src: "b4:skeleton.strike×2",
				d: (c, o) => {
					diagSword(.76)(c, o);
					halo(c, o, (q) => at$1(q, 0, 0, 1, (p) => {
						p.scale(-1, 1);
						diagSword(.76)(p, o);
					}));
				}
			},
			attack: {
				zh: "普通攻擊",
				topic: "斜放的亮色單手劍（同打擊徽章）",
				src: "b4:skeleton.strike",
				d: diagSword()
			},
			tag_push: {
				zh: "推擊技能",
				topic: "朝右上的黃白粗箭頭（同效果「推擊」）",
				src: "b3:push",
				d: act$1("push")
			},
			tag_heal: {
				zh: "治療技能",
				topic: "綠色粗十字（同效果「治療」）",
				src: "b3:heal",
				d: act$1("heal")
			},
			tag_control: {
				zh: "控制技能",
				topic: "一把金鎖（同骨架徽章「控制」）",
				src: "b3:bind",
				d: act$1("bind")
			},
			tag_ranged: {
				zh: "遠程技能",
				topic: "木色弓臂、白弦、一支鋼頭箭朝右",
				d: bowArrow
			},
			tag_shout: {
				zh: "吼叫技能",
				topic: "象牙號角加聲波（同第 3 批中性道具「吼聲」）",
				src: "b3:w:roar",
				d: from48((c, o) => THINGS.roar.d(c, {
					...o,
					small: true
				}), .44)
			},
			tag_area: {
				zh: "範圍技能",
				topic: "向外擴的衝擊環（同骨架徽章「範圍」）",
				src: "b4:skeleton.area",
				d: areaBurst
			},
			tag_summon: {
				zh: "召喚技能",
				topic: "一隻青色小靈（同效果「召喚」；現行畫傷害閃光）",
				src: "b3:summon",
				d: spirit()
			},
			tag_other: {
				zh: "其他標籤的技能",
				topic: "白色四芒閃光（同現行：沒列的標籤畫傷害）",
				src: "b3:hit",
				d: act$1("hit")
			},
			actions: {
				zh: "其他動作",
				topic: "斜放的亮色單手劍（同普通攻擊；現行同一把劍）",
				src: "b4:skeleton.strike",
				d: diagSword()
			},
			default: {
				zh: "沒寫對象（所有技能）",
				topic: "白色四芒閃光（同現行預設）",
				src: "b3:hit",
				d: act$1("hit")
			}
		}
	};
	/** 沒有 Q 版圖樣的狀態由這個掛鉤畫（樣張頁掛上現行的白色狀態圖樣）；沒掛時畫增益箭頭。 */
	var hooks = { status: null };
	function entry(cat, id) {
		if (cat === "effect" && typeof id === "string") {
			if (id.startsWith("status:")) return entry("status", id.slice(7));
			if (id.startsWith("surface:")) return entry("surface", id.slice(8));
			id = EFFECT_ALIAS[id] ?? id;
		}
		if (cat === "trigger") id = TRIG$1[id] ? id : TRIG_ALIAS[id] ?? id;
		if (cat === "condition" && typeof id === "string" && id.startsWith("target_has_status:")) {
			const s = entry("status", id.slice(18));
			return {
				zh: "目標帶有狀態：" + (s.zh ?? id.slice(18)),
				topic: "那個狀態的圖，右上一個問號",
				live: s.live,
				d: (c, o, T, opt) => {
					at$1(c, -1.6, 1.4, .84, (q) => s.d(q, o, T, opt));
					if (!o.tiny) qmark(c, o, 7.4, -6, .8);
				}
			};
		}
		const e = CATS[cat]?.[id];
		if (e) return e;
		if (cat === "status") return {
			zh: id,
			topic: "（沒有 Q 版圖樣：現行圖樣頂著）",
			live: true,
			d: (c, o) => hooks.status ? hooks.status(c, o, id) : ACT.buff.d(c, o, ACT.buff.def)
		};
		return {
			zh: id,
			topic: "（不認得）",
			unknown: true,
			d: (c, o) => qmark(c, {
				...o,
				flat: true
			}, 0, 0, 2)
		};
	}
	/** 圖樣定義（給 QIcons.render；畫在 48 格，±10 單位放大 1.8 倍）。cpx＝圖樣本身（±10 單位）顯示的 CSS px，決定簡化程度。 */
	function def(cat, id, cpx = 20, opt = {}) {
		const e = entry(cat, id);
		return {
			zh: e.zh,
			entry: e,
			d: (c, o) => {
				c.save();
				c.translate(24, 24);
				c.scale(1.8, 1.8);
				e.d(c, {
					...o,
					small: cpx <= 24,
					tiny: cpx <= 14
				}, opt.tint, opt);
				c.restore();
			}
		};
	}
	var BOX = 48 / 36;
	/** 只有圖樣的 canvas（不含圓底）：≤14px 不包外框（規則 8）。 */
	var glyph = (cat, id, cpx, res = 2, opt = {}) => Q.render(def(cat, id, cpx, opt), cpx * BOX, res, { ow: opt.ow ?? (cpx <= 14 ? 0 : Q.outlinePx(cpx)) });
	/** 卡片小圖的圖樣本身（±10 單位）在 px 邊長的格子裡畫多大：最大 14px（≤14px 不包外框，圖樣才撐得滿格子；第 3 批的記號畫到 ±11.6 單位）。 */
	var cardPx = (px) => Math.min(14, px * .84);
	/** 技能卡小圖：px 邊長（常駐行 16、效果行 18、圖釘 13）；圖樣撐滿整格。 */
	function cardCanvas(id, px, zoom = 1, o = {}) {
		const res = o.res ?? (zoom === 1 ? 2 : zoom), cv = blank(Math.round(px * res));
		if (cv.style) cv.style.width = cv.style.height = px * zoom + "px";
		const x = ctxOf(cv);
		const g = glyph("card", id, cardPx(px), res, o);
		if (g) QW.blit(x, g, 0, 0, px * res, 1);
		return cv;
	}
	var statusFit_default = {
		_note: "由開發頁 client/dev/status-gallery.html?set=fitgen 在 Chrome（無頭、--disable-gpu＝軟體繪製，同美術自查表 qicons_shots.py）量出（render/qIcon/status.ts 的 fitKMeasured，樣張 fitK 的逐行搬）；不手改。鍵＝id|框邊長 toFixed(2)|inset toFixed(2)",
		fit: {
			"armor_broken|16.80|0.00": 1,
			"armor_broken|9.00|0.00": .88,
			"array_ward|16.80|0.00": 1,
			"array_ward|9.00|0.00": .92,
			"bleed|16.80|0.00": 1,
			"bleed|9.00|0.00": .92,
			"blinded|16.80|0.00": 1,
			"blinded|9.00|0.00": .96,
			"burning|16.80|0.00": 1,
			"burning|9.00|0.00": .92,
			"charging|16.80|0.00": .9,
			"charging|9.00|0.00": .82,
			"commanding|16.80|0.00": 1,
			"commanding|9.00|0.00": .94,
			"concealed|16.80|0.00": .8,
			"concealed|9.00|0.00": .7,
			"crystal_surge_2|16.80|0.00": .84,
			"crystal_surge_2|9.00|0.00": .78,
			"crystal_surge|16.80|0.00": .86,
			"crystal_surge|9.00|0.00": .78,
			"defending|16.80|0.00": 1,
			"defending|9.00|0.00": .9,
			"empowered|16.80|0.00": .94,
			"empowered|9.00|0.00": .86,
			"entangled|16.80|0.00": 1,
			"entangled|9.00|0.00": .92,
			"feared|16.80|0.00": 1,
			"feared|9.00|0.00": 1,
			"feared|9.00|0.50": 1,
			"feared|9.00|1.00": .82,
			"frost_ember_burst|16.80|0.00": 1,
			"frost_ember_burst|9.00|0.00": .92,
			"frozen|16.80|0.00": 1,
			"frozen|9.00|0.00": 1,
			"frozen|9.00|0.50": .98,
			"frozen|9.00|1.00": .78,
			"guarded|16.80|0.00": 1,
			"guarded|9.00|0.00": 1,
			"hard_shell|16.80|0.00": .98,
			"hard_shell|9.00|0.00": .88,
			"hasted|16.80|0.00": .94,
			"hasted|9.00|0.00": .86,
			"heart_ember_burst|16.80|0.00": 1,
			"heart_ember_burst|9.00|0.00": .88,
			"heart_link|16.80|0.00": 1,
			"heart_link|9.00|0.00": .98,
			"infused_fire|16.80|0.00": 1,
			"infused_fire|9.00|0.00": .98,
			"infused_holy|16.80|0.00": 1,
			"infused_holy|9.00|0.00": .88,
			"league_truce|16.80|0.00": .78,
			"league_truce|9.00|0.00": .72,
			"marked|16.80|0.00": .98,
			"marked|9.00|0.00": .88,
			"mist_return|16.80|0.00": 1,
			"mist_return|9.00|0.00": .92,
			"molten_burst|16.80|0.00": 1,
			"molten_burst|9.00|0.00": .92,
			"molten_shell|16.80|0.00": .96,
			"molten_shell|9.00|0.00": .84,
			"oath_bonus_easy|16.80|0.00": .82,
			"oath_bonus_easy|9.00|0.00": .74,
			"oath_bonus_hard|16.80|0.00": .82,
			"oath_bonus_hard|9.00|0.00": .74,
			"oath_bonus_medium|16.80|0.00": .82,
			"oath_bonus_medium|9.00|0.00": .74,
			"oath_broken|16.80|0.00": .96,
			"oath_broken|9.00|0.00": .88,
			"overdrawn|16.80|0.00": 1,
			"overdrawn|9.00|0.00": .88,
			"overwatch|16.80|0.00": .96,
			"overwatch|9.00|0.00": .86,
			"poison|16.80|0.00": 1,
			"poison|9.00|0.00": 1,
			"prone|16.80|0.00": 1,
			"prone|9.00|0.00": .92,
			"race_adapt|16.80|0.00": .8,
			"race_adapt|9.00|0.00": .76,
			"race_stonewall|16.80|0.00": .76,
			"race_stonewall|9.00|0.00": .7,
			"rallied|16.80|0.00": .92,
			"rallied|9.00|0.00": .82,
			"regenerating|16.80|0.00": .88,
			"regenerating|9.00|0.00": .82,
			"revealed|16.80|0.00": 1,
			"revealed|9.00|0.00": .96,
			"rift_channel|16.80|0.00": 1,
			"rift_channel|9.00|0.00": .96,
			"rift_collapse|16.80|0.00": .84,
			"rift_collapse|9.00|0.00": .76,
			"rift_resonance|16.80|0.00": 1,
			"rift_resonance|9.00|0.00": 1,
			"root|16.80|0.00": 1,
			"root|9.00|0.00": .92,
			"root|9.00|0.50": .82,
			"root|9.00|1.00": .68,
			"shard_burst|16.80|0.00": 1,
			"shard_burst|9.00|0.00": .94,
			"shielded_charged|16.80|0.00": 1,
			"shielded_charged|9.00|0.00": .94,
			"shielded_marking|16.80|0.00": 1,
			"shielded_marking|9.00|0.00": .94,
			"shielded_mending|16.80|0.00": 1,
			"shielded_mending|9.00|0.00": .94,
			"shielded_thorns|16.80|0.00": .88,
			"shielded_thorns|9.00|0.00": .8,
			"shielded_wet|16.80|0.00": 1,
			"shielded_wet|9.00|0.00": .94,
			"shielded|16.80|0.00": .88,
			"shielded|9.00|0.00": .8,
			"silenced|16.80|0.00": 1,
			"silenced|9.00|0.00": 1,
			"silenced|9.00|0.50": .86,
			"silenced|9.00|1.00": .72,
			"slow|16.80|0.00": .98,
			"slow|9.00|0.00": .84,
			"slow|9.00|0.50": .76,
			"slow|9.00|1.00": .6,
			"soul_link|16.80|0.00": .96,
			"soul_link|9.00|0.00": .84,
			"stance_bastion|16.80|0.00": 1,
			"stance_bastion|9.00|0.00": .96,
			"stance_blaze|16.80|0.00": 1,
			"stance_blaze|9.00|0.00": .96,
			"stance_bulwark|16.80|0.00": 1,
			"stance_bulwark|9.00|0.00": .96,
			"stance_earth_1|16.80|0.00": 1,
			"stance_earth_1|9.00|0.00": .96,
			"stance_earth_2|16.80|0.00": 1,
			"stance_earth_2|9.00|0.00": .96,
			"stance_earth_3|16.80|0.00": 1,
			"stance_earth_3|9.00|0.00": .96,
			"stance_earth_4|16.80|0.00": 1,
			"stance_earth_4|9.00|0.00": .96,
			"stance_earth_5|16.80|0.00": 1,
			"stance_earth_5|9.00|0.00": .96,
			"stance_fire_1|16.80|0.00": 1,
			"stance_fire_1|9.00|0.00": .96,
			"stance_fire_2|16.80|0.00": 1,
			"stance_fire_2|9.00|0.00": .96,
			"stance_fire_3|16.80|0.00": 1,
			"stance_fire_3|9.00|0.00": .96,
			"stance_fire_4|16.80|0.00": 1,
			"stance_fire_4|9.00|0.00": .96,
			"stance_fire_5|16.80|0.00": 1,
			"stance_fire_5|9.00|0.00": .96,
			"stance_flame|16.80|0.00": 1,
			"stance_flame|9.00|0.00": .96,
			"stance_frost|16.80|0.00": 1,
			"stance_frost|9.00|0.00": .96,
			"stance_fury|16.80|0.00": 1,
			"stance_fury|9.00|0.00": .96,
			"stance_glacier|16.80|0.00": 1,
			"stance_glacier|9.00|0.00": .96,
			"stance_guard|16.80|0.00": 1,
			"stance_guard|9.00|0.00": .96,
			"stance_holy_1|16.80|0.00": 1,
			"stance_holy_1|9.00|0.00": .96,
			"stance_holy_2|16.80|0.00": 1,
			"stance_holy_2|9.00|0.00": .96,
			"stance_holy_3|16.80|0.00": 1,
			"stance_holy_3|9.00|0.00": .96,
			"stance_holy_4|16.80|0.00": 1,
			"stance_holy_4|9.00|0.00": .96,
			"stance_holy_5|16.80|0.00": 1,
			"stance_holy_5|9.00|0.00": .96,
			"stance_ice_1|16.80|0.00": 1,
			"stance_ice_1|9.00|0.00": .96,
			"stance_ice_2|16.80|0.00": 1,
			"stance_ice_2|9.00|0.00": .96,
			"stance_ice_3|16.80|0.00": 1,
			"stance_ice_3|9.00|0.00": .96,
			"stance_ice_4|16.80|0.00": 1,
			"stance_ice_4|9.00|0.00": .96,
			"stance_ice_5|16.80|0.00": 1,
			"stance_ice_5|9.00|0.00": .96,
			"stance_ironwall|16.80|0.00": 1,
			"stance_ironwall|9.00|0.00": .96,
			"stance_lightning_1|16.80|0.00": 1,
			"stance_lightning_1|9.00|0.00": .96,
			"stance_lightning_2|16.80|0.00": 1,
			"stance_lightning_2|9.00|0.00": .96,
			"stance_lightning_3|16.80|0.00": 1,
			"stance_lightning_3|9.00|0.00": .96,
			"stance_lightning_4|16.80|0.00": 1,
			"stance_lightning_4|9.00|0.00": .96,
			"stance_lightning_5|16.80|0.00": 1,
			"stance_lightning_5|9.00|0.00": .96,
			"stance_physical_1|16.80|0.00": 1,
			"stance_physical_1|9.00|0.00": .96,
			"stance_physical_2|16.80|0.00": 1,
			"stance_physical_2|9.00|0.00": .96,
			"stance_physical_3|16.80|0.00": 1,
			"stance_physical_3|9.00|0.00": .96,
			"stance_physical_4|16.80|0.00": 1,
			"stance_physical_4|9.00|0.00": .96,
			"stance_physical_5|16.80|0.00": 1,
			"stance_physical_5|9.00|0.00": .96,
			"stance_poison_1|16.80|0.00": 1,
			"stance_poison_1|9.00|0.00": .96,
			"stance_poison_2|16.80|0.00": 1,
			"stance_poison_2|9.00|0.00": .96,
			"stance_poison_3|16.80|0.00": 1,
			"stance_poison_3|9.00|0.00": .96,
			"stance_poison_4|16.80|0.00": 1,
			"stance_poison_4|9.00|0.00": .96,
			"stance_poison_5|16.80|0.00": 1,
			"stance_poison_5|9.00|0.00": .96,
			"stance_shadow_1|16.80|0.00": 1,
			"stance_shadow_1|9.00|0.00": .96,
			"stance_shadow_2|16.80|0.00": 1,
			"stance_shadow_2|9.00|0.00": .96,
			"stance_shadow_3|16.80|0.00": 1,
			"stance_shadow_3|9.00|0.00": .96,
			"stance_shadow_4|16.80|0.00": 1,
			"stance_shadow_4|9.00|0.00": .96,
			"stance_shadow_5|16.80|0.00": 1,
			"stance_shadow_5|9.00|0.00": .96,
			"stance_wind_1|16.80|0.00": 1,
			"stance_wind_1|9.00|0.00": .96,
			"stance_wind_2|16.80|0.00": 1,
			"stance_wind_2|9.00|0.00": .96,
			"stance_wind_3|16.80|0.00": 1,
			"stance_wind_3|9.00|0.00": .96,
			"stance_wind_4|16.80|0.00": 1,
			"stance_wind_4|9.00|0.00": .96,
			"stance_wind_5|16.80|0.00": 1,
			"stance_wind_5|9.00|0.00": .96,
			"stoneskin|16.80|0.00": .94,
			"stoneskin|9.00|0.00": .84,
			"stun|16.80|0.00": 1,
			"stun|9.00|0.00": .88,
			"stun|9.00|0.50": .84,
			"stun|9.00|1.00": .72,
			"summit_array_ward|16.80|0.00": .86,
			"summit_array_ward|9.00|0.00": .76,
			"sword_formation|16.80|0.00": .86,
			"sword_formation|9.00|0.00": .76,
			"taunted|16.80|0.00": .98,
			"taunted|9.00|0.00": .88,
			"taunted|9.00|0.50": .72,
			"taunted|9.00|1.00": .6,
			"time_bomb|16.80|0.00": .98,
			"time_bomb|9.00|0.00": .88,
			"undying|16.80|0.00": .9,
			"undying|9.00|0.00": .8,
			"vulnerable|16.80|0.00": 1,
			"vulnerable|9.00|0.00": 1,
			"weaken|16.80|0.00": 1,
			"weaken|9.00|0.00": .88
		}
	};
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/qIcon/status.ts
	/** 樣張 `QIconsParts` 用到的部分。 */
	var QP = {
		entry,
		BOX
	};
	var PI = Math.PI;
	/** 樣張把 "butt" 當 ln 的 lineJoin 傳（瀏覽器忽略這個值；lineCap 因此是 butt），照傳。 */
	var BUTT = "butt";
	var CREAM = "#f2e6c8";
	var GOLD = "#e8bb48";
	var STONE = "#b4ac9a";
	var STONE_L = "#ece6d6";
	var STONE_D = "#8c8474";
	var st = (c, col, w, fn, cap = "round") => {
		c.beginPath();
		fn(c);
		c.strokeStyle = col;
		c.lineWidth = w;
		c.lineCap = cap;
		c.lineJoin = "round";
		c.stroke();
	};
	var at = (c, x, y, k, fn, rot = 0) => {
		c.save();
		c.translate(x, y);
		c.rotate(rot);
		c.scale(k, k);
		fn(c);
		c.restore();
	};
	var fit = (d, k) => (c, o) => at(c, 0, 0, k, (q) => d(q, o));
	/** 第 3 批的效果記號、第 4 批的部件：同一個題材同一個形，直接呼叫。 */
	var act = (id, T) => (c, o) => ACT[id].d(c, o, T ?? ACT[id].def);
	var part = (cat, id) => (c, o) => QP.entry(cat, id).d(c, o);
	/** 窄一號的朝上箭頭（同 upArrow 的配色；晶能狂湧兩個並排時要拉得開）。 */
	var slimArrow = (c, T = ["#ffb23a", "#fff6c8"]) => {
		poly(c, T[0], [
			[0, -11],
			[6, -2],
			[2.6, -2],
			[2.6, 9.6],
			[-2.6, 9.6],
			[-2.6, -2],
			[-6, -2]
		], .6);
		poly(c, T[1], [
			[0, -11],
			[-6, -2],
			[-2.6, -2],
			[-2.6, 9.6],
			[0, 9.6]
		]);
	};
	/** 旗桿（木桿＋金頂珠）：戰意的紅三角旗、開場休戰的白旗共用；旗的形不同（三角 vs 方形波浪）。 */
	var pole = (c) => {
		rr(c, "#a06a36", -8.4, -8.6, 2.8, 19.2, 1.2);
		f(c, "#d8a868", () => c.rect(-8.4, -8.6, 1, 19));
		ci(c, GOLD, -7, -9.4, 2.2);
	};
	/** 誓約徽章：一枚金屬圓章（中間一顆五角星）掛在兩條紅緞帶上；三個難度用銅、銀、金分。 */
	var MEDAL = {
		bronze: [
			"#c27a48",
			"#f0b088",
			"#8a4a22"
		],
		silver: [
			"#d0d8e0",
			"#ffffff",
			"#8a96a4"
		],
		gold: [
			"#e8bb48",
			"#fff0b0",
			"#9c7420"
		]
	};
	var medal = (m) => (c, o) => {
		const [a, b, d] = MEDAL[m];
		for (const s of [-1, 1]) poly(c, s < 0 ? "#d8404a" : "#b02a36", [
			[s * 1.2, 2],
			[s * 6.6, 2],
			[s * 8.2, 10.6],
			[s * 5.4, 8.6],
			[s * 3, 10.6]
		], .3);
		ci(c, a, 0, -2.6, 8);
		f(c, d, () => {
			c.arc(0, -2.6, 8, -.3, PI * .8);
			c.arc(0, -2.6, 6.2, PI * .8, -.3, true);
			c.closePath();
		});
		poly(c, b, starPts(0, -2.6, 5, 2.1, 5), .2);
		if (!o.tiny) el(c, "#ffffff", -4, -6, 1.8, 1.1, -.6);
	};
	/** 熔核：一顆橘紅的熾熱圓核，表面幾塊深色硬殼、殼縫透出黃白的光；寒燼換冰色。 */
	var CORE = {
		lava: [
			"#ff6a1a",
			"#ffe08a",
			"#6a3424",
			"#ffb23a"
		],
		frost: [
			"#5ab8f0",
			"#ffffff",
			"#2a4a7a",
			"#bfefff"
		]
	};
	var core = (kind, R = 9.4) => (c, _o) => {
		const [body, glow, crust, mid] = CORE[kind];
		ci(c, body, 0, .4, R);
		ci(c, mid, -1, -.4, R * .62);
		ci(c, glow, -1.4, -.8, R * .3);
		const k = R / 9.4;
		for (const P of [
			[
				[-9, -2.4],
				[-4.6, -8.2],
				[-1.6, -4.4],
				[-5, -.6]
			],
			[
				[2.6, -8.6],
				[8.4, -4.6],
				[5.4, -1.4],
				[1.2, -3.8]
			],
			[
				[-6.2, 5.4],
				[-1.6, 3.4],
				[.6, 8.8],
				[-3.6, 9.4]
			],
			[
				[4.2, 2.6],
				[9.2, 2.2],
				[6.8, 7.8],
				[3.2, 6.6]
			]
		]) poly(c, crust, P.map(([x, y]) => [x * k, y * k + .4]), .3);
	};
	/** 龜殼形的殼（熔殼、硬殼）：上緣圓、下緣一排小圓弧（殼的邊片），殼面中間一塊六角殼片、四周放射的縫；不畫帽簷（第 1 稿有一條橫的底座，像安全帽）。 */
	var dome = (body, hi, seam, w = 1.6, rim = body) => (c, _o) => {
		f(c, body, () => {
			c.moveTo(-10.4, 4.6);
			c.bezierCurveTo(-10.6, -11.4, 10.6, -11.4, 10.4, 4.6);
			c.closePath();
		});
		for (let i = 0; i < 5; i++) ci(c, rim, -8.4 + i * 4.2, 4.8, 2.4);
		f(c, hi, () => {
			c.moveTo(-8.4, 1.6);
			c.bezierCurveTo(-8.4, -5.6, -4.6, -8, -1.4, -8.4);
			c.lineTo(-1.6, -6.4);
			c.bezierCurveTo(-4.4, -5.8, -6.4, -3.6, -6.4, 1.6);
			c.closePath();
		});
		const H = [
			[-3.4, -5],
			[3.4, -5],
			[5, -1],
			[3.4, 2.6],
			[-3.4, 2.6],
			[-5, -1]
		];
		ln(c, seam, w, [...H, H[0]]);
		for (const [a, b] of [
			[H[0], [-5.6, -8.6]],
			[H[1], [5.6, -8.6]],
			[H[2], [10.2, -1]],
			[H[5], [-10.2, -1]],
			[H[3], [5.4, 4.6]],
			[H[4], [-5.4, 4.6]]
		]) ln(c, seam, w, [a, b]);
	};
	var NEW = {
		revealed: {
			zh: "被揭露",
			topic: "睜開的眼睛（同效果「揭露」）",
			src: "b4:effect.reveal",
			d: part("effect", "reveal")
		},
		time_bomb: {
			zh: "定時炸彈",
			topic: "圓炸彈、引信頭黃火花（同效果「定時炸彈」）",
			src: "b4:effect.delayed_damage",
			d: part("effect", "delayed_damage")
		},
		shielded: {
			zh: "護盾",
			topic: "淡藍小盾、白十字（同效果「護盾」）",
			src: "b3:shield",
			d: act("shield")
		},
		undying: {
			zh: "免死",
			topic: "紅心、右下一面小藍盾（同效果「免死」）",
			src: "b4:effect.cheat_death",
			d: part("effect", "cheat_death")
		},
		soul_link: {
			zh: "靈魂連結",
			topic: "兩個扣在一起的淡紫圓環（前後交扣）",
			d: (c, o) => {
				const ring = (q, x, a0 = 0, a1 = TAU$3) => st(q, "#c8a0ff", o.tiny ? 3.2 : 2.8, (p) => p.arc(x, .4, 5.6, a0, a1), "butt");
				ring(c, -3.8);
				halo(c, o, (q) => {
					ring(q, 3.8);
					if (!o.tiny) st(q, "#efe2ff", 1.1, (p) => p.arc(3.8, .4, 5.6, PI * 1.15, PI * 1.55), "butt");
				});
				halo(c, o, (q) => ring(q, -3.8, -.75, .05));
				if (!o.tiny) st(c, "#efe2ff", 1.1, (p) => p.arc(-3.8, .4, 5.6, PI * 1.15, PI * 1.55), "butt");
			}
		},
		shielded_thorns: {
			zh: "反傷護盾",
			topic: "淡藍盾，盾緣往外長出五根鐵刺",
			d: fit((c, o) => {
				halo(c, o, (q) => {
					for (const [x, y, a] of [
						[
							-9.4,
							-9.6,
							-2.36
						],
						[
							9.4,
							-9.6,
							-.79
						],
						[
							0,
							-9.6,
							-1.57
						],
						[
							-9.2,
							-2,
							-2.9
						],
						[
							9.2,
							-2,
							-.24
						]
					]) at(q, x, y, 1, (p) => poly(p, "#7d8794", [
						[0, -2.2],
						[4.6, 0],
						[0, 2.2]
					], .3), a);
				});
				shieldBlue(c, o);
				halo(c, o, (q) => poly(q, "#5a6169", [
					[-4.6, 3.6],
					[0, -5.4],
					[4.6, 3.6],
					[0, 1.2]
				], .3));
			}, .8)
		},
		shielded_mending: {
			zh: "回春護盾",
			topic: "淡藍盾、盾面一株綠芽（同狀態「再生」的嫩芽）",
			d: fit((c, o) => {
				shieldBlue(c, o);
				halo(c, o, (q) => at(q, 0, -.6, .62, (p) => QP.entry("status", "regenerating").d(p, o)));
			}, .86)
		},
		shielded_wet: {
			zh: "水幕護盾",
			topic: "淡藍盾、盾面一顆深藍水滴",
			d: fit((c, o) => {
				shieldBlue(c, o);
				halo(c, o, (q) => {
					drop$2(q, "#2a78d8", 0, -.6, .58);
					if (!o.tiny) el(q, "#cfe8ff", -1.6, .6, .9, 1.6, .4);
				});
			}, .86)
		},
		shielded_marking: {
			zh: "烙印護盾",
			topic: "淡藍盾、盾面一個紅準星（同狀態「被標記」）",
			d: fit((c, o) => {
				shieldBlue(c, o);
				halo(c, o, (q) => at(q, 0, -1, .56, (p) => ACT.mark.d(p, o, ACT.mark.def)));
			}, .86)
		},
		stance_flame: {
			zh: "焰刃姿態",
			topic: "焦橘臂章、一把刃換成黃白的斜劍（劍尖一撮火）",
			d: stancePlate("#c4481c", "#f08a58", (c, o) => {
				at(c, 0, 0, .56, (q) => diagSword(1, [
					"#ffe08a",
					"#ffffff",
					"#ffb23a"
				])(q, o));
				if (!o.tiny) flame$1(c, "#ffffff", 4.4, -4.6, .2);
			})
		},
		stance_blaze: {
			zh: "烈焰姿態",
			topic: "酒紅臂章、一把大白刃斜劍為主，劍後左下一小團黃火",
			d: stancePlate("#b0283e", "#e8708a", (c, o) => {
				flame$1(c, "#ffd23f", -3.2, 3.6, .36);
				at(c, .6, -.4, .66, (q) => diagSword(1, [
					"#ffffff",
					"#ffffff",
					"#ffe08a"
				])(q, o));
			})
		},
		stance_frost: {
			zh: "霜刃姿態",
			topic: "冰藍臂章、一把淡青白刃的大斜劍",
			d: stancePlate("#3a7cc0", "#86b8e8", (c, o) => at(c, .4, -.4, .66, (q) => diagSword(1, [
				"#e8faff",
				"#ffffff",
				"#8fe3ff"
			])(q, o)))
		},
		stance_glacier: {
			zh: "冰川姿態",
			topic: "深藍臂章、三根白色冰柱（中間高）",
			d: stancePlate("#2a5aa8", "#6a9ad8", (c, _o) => {
				poly(c, "#d8f6ff", [
					[-6.4, 6],
					[-6.4, -.6],
					[-4.4, -3.6],
					[-2.4, -.6],
					[-2.4, 6]
				], .3);
				poly(c, "#d8f6ff", [
					[2.4, 6],
					[2.4, -.6],
					[4.4, -3.6],
					[6.4, -.6],
					[6.4, 6]
				], .3);
				poly(c, "#ffffff", [
					[-2.2, 6],
					[-2.2, -3.6],
					[0, -7.4],
					[2.2, -3.6],
					[2.2, 6]
				], .3);
			})
		},
		stance_bastion: {
			zh: "堡壘姿態",
			topic: "石板灰臂章、一座米白的城塔（頂上三個垛口）",
			d: stancePlate("#5a6478", "#8e9aae", (c, o) => {
				f(c, "#f2ead6", () => {
					c.moveTo(-5.2, 6.6);
					c.lineTo(-5.2, -6.6);
					c.lineTo(-2.6, -6.6);
					c.lineTo(-2.6, -4.4);
					c.lineTo(-.9, -4.4);
					c.lineTo(-.9, -6.6);
					c.lineTo(.9, -6.6);
					c.lineTo(.9, -4.4);
					c.lineTo(2.6, -4.4);
					c.lineTo(2.6, -6.6);
					c.lineTo(5.2, -6.6);
					c.lineTo(5.2, 6.6);
					c.closePath();
				});
				f(c, "#4a5262", () => c.roundRect(-1.6, 1.4, 3.2, 5.2, [
					1.6,
					1.6,
					0,
					0
				]));
				if (!o.tiny) f(c, "#c8bea6", () => c.rect(2.6, -4.4, 2.6, 11));
			})
		},
		race_adapt: {
			zh: "應變",
			topic: "米白人形往右閃，背後兩道速度線，一支紅箭頭從頭頂上面擦過去",
			d: (c, o) => {
				for (const [y, w] of [[-1.4, 6.4], [3.4, 4.6]]) rr(c, CREAM, -10.6, y, w, 2.4, 1.2);
				bust(c, CREAM, 3, 2.4, 1.02);
				halo(c, o, (q) => {
					ln(q, "#ff5a5a", 2.2, [[-9.4, -8.6], [5, -8.6]]);
					poly(q, "#ff5a5a", [
						[4.4, -11.6],
						[10.4, -8.6],
						[4.4, -5.6]
					], .3);
				});
			}
		},
		race_stonewall: {
			zh: "穩若磐石",
			topic: "一塊寬大的平頂多面灰岩，左下一支紅箭頭撞在岩面上、撞點一顆黃火花",
			d: (c, o) => {
				poly(c, STONE, [
					[-4.4, 8.4],
					[-6.6, 1.6],
					[-4.2, -5.4],
					[4.4, -6.6],
					[10.4, -2.4],
					[10.6, 5.4],
					[7.6, 8.4]
				], .6);
				poly(c, STONE_L, [
					[-6.6, 1.6],
					[-4.2, -5.4],
					[4.4, -6.6],
					[10.4, -2.4],
					[3.2, -1],
					[-2.4, .6]
				]);
				poly(c, STONE_D, [
					[10.4, -2.4],
					[10.6, 5.4],
					[7.6, 8.4],
					[3.6, 8.4],
					[3.2, -1]
				]);
				if (!o.tiny) ln(c, STONE_D, 1, [[-2.4, .6], [-1.4, 8.4]]);
				halo(c, o, (q) => {
					ln(q, "#ff4a4a", 2.6, [[-10.8, 10], [-7.4, 6.6]], BUTT);
					poly(q, "#ff4a4a", [
						[-9.6, 3.6],
						[-4.8, 4],
						[-5.4, 8.8]
					], .3);
				});
				halo(c, o, (q) => star4(q, "#ffd23f", -5.2, 3.4, 3.6, o.tiny ? null : "#ffffff"));
			}
		},
		rallied: {
			zh: "戰意",
			topic: "木旗桿上一面紅色三角旗",
			d: (c, _o) => {
				pole(c);
				poly(c, "#e8403a", [
					[-5.6, -8.4],
					[10.4, -3.6],
					[-5.6, 1.4]
				], .6);
				poly(c, "#ff8a7a", [
					[-5.6, -8.4],
					[10.4, -3.6],
					[-5.6, -4.6]
				]);
			}
		},
		league_truce: {
			zh: "開場休戰",
			topic: "木旗桿上一面白旗（方形、右緣波浪）",
			d: (c, _o) => {
				pole(c);
				f(c, "#f6f2e6", () => {
					c.moveTo(-5.6, -8.8);
					c.lineTo(9.4, -8.8);
					c.quadraticCurveTo(7.4, -6, 9.8, -3.6);
					c.quadraticCurveTo(11, -1, 9.4, 1.6);
					c.lineTo(-5.6, 1.6);
					c.closePath();
				});
				f(c, "#c8c0ac", () => {
					c.moveTo(-5.6, -2);
					c.lineTo(9.6, -2);
					c.quadraticCurveTo(11, -.4, 9.4, 1.6);
					c.lineTo(-5.6, 1.6);
					c.closePath();
				});
			}
		},
		commanding: {
			zh: "號令",
			topic: "青色小靈（召喚物），右上一個橘黃的朝上箭頭",
			d: (c, o) => {
				at(c, -2, 1.8, .84, (q) => ACT.summon.d(q, o, ACT.summon.def));
				halo(c, o, (q) => at(q, 6, -5.6, .46, (p) => upArrow(p, o)));
			}
		},
		armor_broken: {
			zh: "破甲",
			topic: "亮鋼灰胸甲（T 字形：寬肩甲、挖進去的袖洞、深 V 領），一道深色裂縫，右下崩掉一塊",
			d: (c, o) => {
				const P = [
					[-10.6, -6.2],
					[-7.8, -9.8],
					[-3.8, -9.8],
					[0, -2.6],
					[3.8, -9.8],
					[7.8, -9.8],
					[10.6, -6.2],
					[9.8, -2],
					[6.4, -1.4],
					[6.6, 9.8],
					[-6.6, 9.8],
					[-6.4, -1.4],
					[-9.8, -2]
				];
				c.save();
				c.beginPath();
				P.forEach(([x, y], i) => i ? c.lineTo(x, y) : c.moveTo(x, y));
				c.closePath();
				c.moveTo(7, 2.6);
				c.lineTo(3, 5);
				c.lineTo(4, 10.4);
				c.lineTo(7.4, 10.4);
				c.closePath();
				c.clip("evenodd");
				poly(c, "#a4aebb", P, .6);
				poly(c, "#d2d9e2", [
					[-10.6, -6.2],
					[-7.8, -9.8],
					[-3.8, -9.8],
					[0, -2.6],
					[0, 9.8],
					[-6.6, 9.8],
					[-6.4, -1.4],
					[-9.8, -2]
				]);
				f(c, "#7d8794", () => c.rect(4.2, -1.4, 2.6, 11.4));
				f(c, "#8a96a4", () => c.rect(-6.6, 4, 13.2, 1.6));
				c.restore();
				ln(c, OUT, 1.7, [
					[.2, -2.2],
					[-1.4, .8],
					[1.2, 3.4],
					[-.6, 6.4],
					[.6, 9.6]
				], "miter");
				halo(c, o, (q) => poly(q, "#a4aebb", [
					[10.4, 4.4],
					[7.8, 6],
					[8.4, 9.8],
					[10.8, 8.8]
				], .3));
			}
		},
		entangled: {
			zh: "纏繞",
			topic: "褐色靴子（同 HUD「移動」）的靴筒被兩圈淡褐繩子纏住",
			d: (c, o) => {
				at(c, .6, .6, .47, (q) => {
					q.translate(-27, -24);
					ART.hud.move.d(q, o);
				});
				halo(c, o, (q) => {
					for (const y of [-6.4, -1.2]) ln(q, "#ecc890", 2.6, [[-8.6, y + 2.4], [7.2, y - 1.8]]);
					ln(q, "#ecc890", 2.2, [[7.2, -3], [10, -7.4]]);
				});
			}
		},
		overdrawn: {
			zh: "透支",
			topic: "黃閃電（同卡片 AP），右下一個紅色減號",
			d: (c, o) => {
				at(c, -1.6, -.6, .95, (q) => bolt(q, o));
				halo(c, o, (q) => rr(q, "#ff5a5a", 2.6, 5.4, 8.6, 3.4, 1.2));
			}
		},
		heart_link: {
			zh: "連心",
			topic: "兩顆疊著的心（後面粉、前面紅）",
			d: (c, o) => {
				heart$1(c, "#f49ab0", -3.6, -1.8, .86);
				if (!o.tiny) el(c, "#ffd8e0", -7, -4.6, 1.8, 1.1, -.6);
				halo(c, o, (q) => {
					heart$1(q, "#f0503e", 3.4, 2.6, .9);
					if (!o.tiny) el(q, "#ffb0a0", .4, .4, 1.8, 1.1, -.6);
				});
			}
		},
		mist_return: {
			zh: "歸一",
			topic: "一道灰白的霧旋往中心收，中心一個綠十字（回血）",
			d: (c, o) => {
				st(c, "#dfe4ee", 3, (x) => {
					x.arc(0, 0, 8.6, PI * .9, PI * 2.1);
				}, "butt");
				st(c, "#b8c0d0", 2.6, (x) => {
					x.arc(.6, .6, 5.4, PI * 1.9, PI * 3);
				}, "butt");
				halo(c, o, (q) => {
					rr(q, "#5ad06a", -1.5, -4.2, 3, 8.4, .8);
					rr(q, "#5ad06a", -4.2, -1.5, 8.4, 3, .8);
				});
			}
		},
		sword_formation: {
			zh: "劍陣",
			topic: "三把並排直立的亮劍（中間那把高一點）",
			d: (c, o) => {
				for (const x of [-6.4, 6.4]) at(c, x, 1.6, .6, (q) => bladeSword(q, o));
				halo(c, o, (q) => at(q, 0, -.4, .68, (p) => bladeSword(p, o)));
			}
		},
		array_ward: {
			zh: "護陣",
			topic: "地上一圈青綠的陣紋環，中心一顆陣眼玉石",
			d: (c, o) => {
				st(c, "#5ad0b0", 3, (x) => x.arc(0, 0, 8.8, 0, TAU$3));
				if (!o.tiny) for (let i = 0; i < 6; i++) ci(c, "#c8fff0", Math.cos(i / 6 * TAU$3) * 8.8, Math.sin(i / 6 * TAU$3) * 8.8, 1);
				poly(c, "#7fe0c0", [
					[0, -5.6],
					[4.4, 0],
					[0, 5.6],
					[-4.4, 0]
				], .4);
				poly(c, "#e6fff6", [
					[0, -5.6],
					[-4.4, 0],
					[0, 0]
				]);
			}
		},
		summit_array_ward: {
			zh: "鎖霧大陣",
			topic: "同護陣的陣紋環與陣眼，下半一團灰白的霧",
			d: (c, o) => {
				NEW["array_ward"].d(c, o);
				halo(c, o, (q) => {
					for (const [x, y, r] of [
						[
							-5.4,
							6.4,
							3.6
						],
						[
							0,
							5.4,
							4.2
						],
						[
							5.4,
							6.6,
							3.4
						]
					]) ci(q, "#e4e8f0", x, y, r);
					rr(q, "#e4e8f0", -8.6, 6.4, 17.2, 3.6, 1.8);
					if (!o.tiny) f(q, "#b8c0d0", () => q.rect(-8.6, 8.6, 17.2, 1.4));
				});
			}
		},
		shard_burst: {
			zh: "碎晶",
			topic: "淡紫源晶裂成兩半往兩邊散開，右下一顆藍水滴（晶液）",
			d: (c, o) => {
				c.save();
				c.beginPath();
				c.moveTo(-12, -12);
				c.lineTo(1.4, -12);
				c.lineTo(-1.2, -2);
				c.lineTo(1.6, 3);
				c.lineTo(-.6, 12);
				c.lineTo(-12, 12);
				c.closePath();
				c.clip();
				at(c, -1.8, -.6, .92, crystal);
				c.restore();
				c.save();
				c.beginPath();
				c.moveTo(12, -12);
				c.lineTo(1.4, -12);
				c.lineTo(-1.2, -2);
				c.lineTo(1.6, 3);
				c.lineTo(-.6, 12);
				c.lineTo(12, 12);
				c.closePath();
				c.clip();
				at(c, 1.8, .4, .92, crystal);
				c.restore();
				if (!o.tiny) halo(c, o, (q) => drop$2(q, "#4aa8ff", 7.4, 6.6, .3));
			}
		},
		rift_resonance: {
			zh: "源晶共鳴",
			topic: "淡紫源晶，左右各兩道往外的共鳴弧",
			d: (c, o) => {
				at(c, 0, 0, .66, crystal);
				for (const s of [-1, 1]) {
					st(c, "#e0d4ff", 2.2, (x) => x.arc(0, 0, 7.6, s > 0 ? -.6 : PI - .6, s > 0 ? .6 : PI + .6), "round");
					if (!o.tiny) st(c, "#b8a8ff", 1.8, (x) => x.arc(0, 0, 10.2, s > 0 ? -.5 : PI - .5, s > 0 ? .5 : PI + .5), "round");
				}
			}
		},
		rift_channel: {
			zh: "灌注源晶",
			topic: "中間一顆淡紫源晶，三道光往外灌進三根小晶柱",
			d: (c, o) => {
				for (let i = 0; i < 3; i++) {
					const a = -PI / 2 + i * TAU$3 / 3, x = Math.cos(a) * 8, y = Math.sin(a) * 8;
					ln(c, "#d6ccff", 1.8, [[Math.cos(a) * 3.6, Math.sin(a) * 3.6], [x, y]]);
					poly(c, "#b8a8ff", [
						[x, y - 3],
						[x + 2, y - 1],
						[x + 2, y + 2.4],
						[x - 2, y + 2.4],
						[x - 2, y - 1]
					], .3);
				}
				halo(c, o, (q) => at(q, 0, 0, .46, crystal));
			}
		},
		crystal_surge: {
			zh: "晶能湧動",
			topic: "淡紫源晶，右上一個橘黃的朝上箭頭",
			d: (c, o) => {
				at(c, -2.2, 1.6, .82, crystal);
				halo(c, o, (q) => at(q, 6, -5.8, .46, (p) => upArrow(p, o)));
			}
		},
		crystal_surge_2: {
			zh: "晶能狂湧",
			topic: "淡紫源晶，上方兩個並排拉開的橘黃朝上箭頭",
			d: (c, o) => {
				at(c, -3, 2.6, .72, crystal);
				for (const x of [1.2, 8]) halo(c, o, (q) => at(q, x, -5.4, .42, (p) => slimArrow(p)));
			}
		},
		rift_collapse: {
			zh: "界崩",
			topic: "一塊灰石浮台（平頂、底下尖）從中間裂開，右半塊往下掉、歪一邊，底下兩顆碎石",
			d: (c, _o) => {
				const half = (s) => (q) => {
					q.save();
					q.scale(s, 1);
					poly(q, STONE, [
						[.4, -4.4],
						[9.6, -4.4],
						[8.4, -.6],
						[3.6, 5.6],
						[.4, 6.4],
						[1.8, 2],
						[-.2, -1.2]
					], .4);
					f(q, STONE_L, () => q.rect(.6, -4.4, 9, 1.8));
					poly(q, STONE_D, [
						[9.6, -2.6],
						[8.4, -.6],
						[3.6, 5.6],
						[5, -.6]
					]);
					q.restore();
				};
				at(c, -.6, -4, 1, half(-1), 0);
				at(c, 1.6, -.6, 1, half(1), .42);
				for (const [x, y, r] of [[
					-1.6,
					7.4,
					1.8
				], [
					1.4,
					9.8,
					1.3
				]]) poly(c, STONE_D, [
					[x - r, y],
					[x, y - r],
					[x + r, y],
					[x, y + r]
				], .3);
			}
		},
		charging: {
			zh: "蓄力",
			topic: "一顆黃白的能量球，外面兩道往內捲的橘色弧",
			d: (c, _o) => {
				for (let i = 0; i < 2; i++) st(c, "#ffb23a", 2.8, (x) => x.arc(0, 0, 8.6, i * PI + .2, i * PI + 1.9), "round");
				for (let i = 0; i < 2; i++) at(c, Math.cos(i * PI + 1.9) * 8.6, Math.sin(i * PI + 1.9) * 8.6, 1, (q) => poly(q, "#ffb23a", [
					[-3, -2.4],
					[3, -2.4],
					[0, 2.4]
				], .3), i * PI + 1.9 + PI);
				ci(c, "#ffe08a", 0, 0, 5);
				ci(c, "#ffffff", -.8, -.8, 2.4);
			}
		},
		oath_bonus_easy: {
			zh: "誓約之力・易",
			topic: "銅色誓約徽章（紅緞帶、中間一顆星）",
			d: medal("bronze")
		},
		oath_bonus_medium: {
			zh: "誓約之力・中",
			topic: "銀色誓約徽章",
			d: medal("silver")
		},
		oath_bonus_hard: {
			zh: "誓約之力・難",
			topic: "金色誓約徽章",
			d: medal("gold")
		},
		oath_broken: {
			zh: "破誓",
			topic: "金色誓約徽章被一道紅斜槓劃掉",
			d: (c, o) => {
				medal("gold")(c, o);
				halo(c, o, (q) => {
					if (o.tiny) ln(q, OUT, 5.4, [[-8.6, 8.6], [8.6, -8.6]]);
					ln(q, "#ff4a5a", 3.4, [[-8.6, 8.6], [8.6, -8.6]]);
				});
			}
		},
		molten_burst: {
			zh: "熔核爆裂",
			topic: "一顆橘紅熾熱的熔核（幾塊深色硬殼、殼縫透黃光）",
			d: core("lava")
		},
		heart_ember_burst: {
			zh: "殼縫熔核",
			topic: "同熔核，左上蓋著一片灰色的殼",
			d: (c, o) => {
				at(c, 1.4, 1.4, .86, (q) => core("lava")(q, o));
				halo(c, o, (q) => {
					f(q, "#9a928a", () => {
						q.moveTo(-10.6, 3);
						q.bezierCurveTo(-11, -8, -4, -11, 4, -10);
						q.lineTo(2.6, -6.6);
						q.bezierCurveTo(-3, -7, -7, -4, -6.6, 3);
						q.closePath();
					});
					if (!o.tiny) f(q, "#d0c8bc", () => {
						q.moveTo(-9.4, -1);
						q.bezierCurveTo(-9.4, -6, -5.6, -8.6, -1, -9.2);
						q.lineTo(-1.4, -8);
						q.bezierCurveTo(-5, -7.4, -7.8, -5, -8, -1);
						q.closePath();
					});
				});
			}
		},
		frost_ember_burst: {
			zh: "寒燼爆裂",
			topic: "一顆冰藍的寒燼核（深藍硬殼、殼縫透白光）",
			d: core("frost")
		},
		molten_shell: {
			zh: "熔殼",
			topic: "暗紅褐的龜殼形外殼（中間一塊六角殼片），殼片之間的縫透橘光",
			d: (c, o) => dome("#8a3a22", "#c46a42", "#ffb23a", 1.8, "#6a2a18")(c, o)
		},
		hard_shell: {
			zh: "硬殼",
			topic: "灰褐色的龜殼形硬殼（中間一塊六角殼片），殼片之間深色的縫",
			d: (c, o) => dome("#b0a084", "#e6dac2", "#5e4a3a", 1.6, "#8a7a62")(c, o)
		}
	};
	statusFit_default.fit;
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/statusIcon.ts
	var TAU$1 = Math.PI * 2;
	/** 舊圖樣色（部件圓片用）：控制類依 control_group。狀態框的類別色改成框底色（`qIcon/status.ts` 的 `CLASS_BG`）。 */
	var CTRL_COLOR = {
		hard: "#ffd84a",
		movement: "#6ac8ff",
		mental: "#c890ff"
	};
	var POL_COLOR = {
		buff: "#7dffb0",
		debuff: "#ff8a8a",
		neutral: "#e8d8a8"
	};
	/** 少數保留自己顏色的狀態（原本的辨識度；圖樣查表的一部分）。 */
	var OWN_COLOR = {
		time_bomb: "#ffb03a",
		shielded: "#8ac8ff",
		guarded: "#8ac8ff",
		stoneskin: "#c8a060",
		defending: "#8ac8ff",
		entangled: "#6ac8ff",
		regenerating: "#7dffb0",
		undying: "#ff8a9a",
		soul_link: "#c8a0ff",
		revealed: "#ffd04a",
		marked: "#ff6a4a",
		overwatch: "#ffd04a",
		infused_fire: "#ff6a1a",
		infused_holy: "#ffe9a0"
	};
	/** 舊圖樣顏色（部件圓片 `skillParts.statusColor` 用；狀態框不再用）：`control_group` → 持續傷害元素 → 專屬色 → `polarity`。 */
	function glyphColor(id) {
		const look = id == null ? void 0 : statusLook(id);
		const ctrl = look?.control_group;
		if (ctrl != null) {
			const c = CTRL_COLOR[ctrl];
			if (c !== void 0) return c;
		}
		if (look?.dot_element != null) return elementColor(look.dot_element);
		return (id == null ? void 0 : OWN_COLOR[id]) ?? POL_COLOR[polarityOf(id)];
	}
	function line(c, pts) {
		c.beginPath();
		pts.forEach(([px, py], i) => i > 0 ? c.lineTo(px, py) : c.moveTo(px, py));
		c.stroke();
	}
	function circle(c, x, y, r, fill = false) {
		c.beginPath();
		c.arc(x, y, r, 0, TAU$1);
		if (fill) c.fill();
		else c.stroke();
	}
	function shield(c) {
		c.beginPath();
		c.moveTo(0, -9);
		c.lineTo(8, -6);
		c.quadraticCurveTo(8, 5, 0, 10);
		c.quadraticCurveTo(-8, 5, -8, -6);
		c.closePath();
		c.stroke();
	}
	function arrow$1(c, x, y, up) {
		const s = up ? -1 : 1;
		line(c, [[x, y - 5 * s], [x, y + 5 * s]]);
		line(c, [
			[x - 4, y - 1 * s],
			[x, y - 5 * s],
			[x + 4, y - 1 * s]
		]);
	}
	function eye$1(c, open) {
		c.beginPath();
		c.moveTo(-10, 0);
		c.quadraticCurveTo(0, -9, 10, 0);
		c.quadraticCurveTo(0, 9, -10, 0);
		c.stroke();
		if (open) circle(c, 0, 0, 3.5, true);
	}
	function star$1(c, x, y, r) {
		c.beginPath();
		for (let i = 0; i < 10; i++) {
			const rad = i % 2 === 1 ? r * .45 : r;
			const a = i / 10 * TAU$1 - Math.PI / 2;
			c.lineTo(x + Math.cos(a) * rad, y + Math.sin(a) * rad);
		}
		c.closePath();
		c.fill();
	}
	function flame(c, x, y, h) {
		c.beginPath();
		c.moveTo(x, y - h);
		c.quadraticCurveTo(x + h * .6, y - h * .2, x + h * .35, y + h * .3);
		c.quadraticCurveTo(x, y + h * .5, x - h * .35, y + h * .3);
		c.quadraticCurveTo(x - h * .6, y - h * .2, x, y - h);
		c.fill();
	}
	function drop$1(c, x, y, s) {
		c.beginPath();
		c.moveTo(x, y - s);
		c.quadraticCurveTo(x + s * .8, y + s * .2, x, y + s * .7);
		c.quadraticCurveTo(x - s * .8, y + s * .2, x, y - s);
		c.fill();
	}
	function sword(c) {
		line(c, [[-6, 7], [6, -7]]);
		line(c, [[-7, 2], [-2, 7]]);
	}
	var STANCE_ELEMENTS = [
		"physical",
		"fire",
		"ice",
		"lightning",
		"poison",
		"wind",
		"earth",
		"holy",
		"shadow"
	];
	var STANCE_LEVELS = 5;
	function elementMark(c, element) {
		switch (element) {
			case "fire":
				c.beginPath();
				c.arc(7, -5, 3, 0, TAU$1);
				c.fill();
				break;
			case "ice":
				line(c, [[4, -5], [10, -5]]);
				line(c, [[7, -8], [7, -2]]);
				break;
			case "lightning":
				line(c, [
					[5, -9],
					[8, -5],
					[5, -4],
					[8, 0]
				]);
				break;
			case "poison":
				c.beginPath();
				c.arc(7, -4, 2.5, 0, TAU$1);
				c.stroke();
				break;
			case "wind":
				line(c, [[3, -7], [10, -7]]);
				line(c, [[4, -3], [9, -3]]);
				break;
			case "earth":
				c.strokeRect(4, -9, 6, 6);
				break;
			case "holy":
				line(c, [[7, -9], [7, -1]]);
				line(c, [[3, -5], [11, -5]]);
				break;
			case "shadow":
				c.beginPath();
				c.arc(7, -5, 3.5, Math.PI * .5, Math.PI * 1.5);
				c.stroke();
		}
	}
	function elementStanceGlyphs() {
		const out = {};
		for (const element of STANCE_ELEMENTS) for (let level = 1; level <= STANCE_LEVELS; level++) out[`stance_${element}_${level}`] = (c) => {
			line(c, [[-8, 5], [4, -7]]);
			line(c, [[-9, 0], [-4, 5]]);
			elementMark(c, element);
			for (let i = 0; i < level; i++) {
				c.beginPath();
				c.arc(-8 + i * 4, 10, 1.2, 0, TAU$1);
				c.fill();
			}
		};
		return out;
	}
	/** 一個狀態一個圖樣（圖樣查表；不認得的狀態畫名稱第一個字）。 */
	var GLYPH = {
		...elementStanceGlyphs(),
		defending: (c) => shield(c),
		guarded: (c) => {
			shield(c);
			arrow$1(c, 0, .5, false);
		},
		stoneskin: (c) => {
			shield(c);
			line(c, [
				[-3, -4],
				[0, -1],
				[-2, 2],
				[1, 5]
			]);
			line(c, [[0, -1], [4, 0]]);
		},
		shielded_thorns: (c) => {
			shield(c);
			line(c, [
				[-3, 2],
				[0, -3],
				[3, 2]
			]);
		},
		shielded_mending: (c) => {
			shield(c);
			line(c, [[0, -4], [0, 4]]);
			line(c, [[-4, 0], [4, 0]]);
		},
		shielded_wet: (c) => {
			shield(c);
			c.beginPath();
			c.arc(0, 1, 2.5, 0, TAU$1);
			c.stroke();
		},
		shielded_marking: (c) => {
			shield(c);
			c.beginPath();
			c.arc(0, 0, 3, 0, TAU$1);
			c.fill();
		},
		shielded_charged: (c) => {
			shield(c);
			line(c, [
				[1, -4],
				[-2, 0],
				[2, 0],
				[-1, 4]
			]);
		},
		shielded: (c) => {
			circle(c, 0, 0, 9);
			c.globalAlpha *= .35;
			c.fill();
			c.globalAlpha /= .35;
			c.beginPath();
			c.arc(0, 0, 5, Math.PI * 1.1, Math.PI * 1.55);
			c.strokeStyle = "#ffffff";
			c.stroke();
		},
		prone: (c) => {
			circle(c, -6, 3, 3, true);
			line(c, [[-2, 4], [9, 4]]);
			line(c, [[-10, 8], [10, 8]]);
		},
		burning: (c) => flame(c, 0, 1, 10),
		poison: (c) => {
			drop$1(c, 0, 0, 10);
			c.fillStyle = "#1a2a10";
			c.beginPath();
			c.arc(-2, 2, 2, 0, TAU$1);
			c.arc(3, -1, 1.4, 0, TAU$1);
			c.fill();
		},
		bleed: (c) => {
			drop$1(c, -3, -1, 7);
			drop$1(c, 5, 3, 5);
		},
		concealed: (c) => {
			c.globalAlpha *= .55;
			circle(c, 0, -4, 4, true);
			c.beginPath();
			c.moveTo(-8, 9);
			c.quadraticCurveTo(0, -2, 8, 9);
			c.fill();
			c.globalAlpha /= .55;
			line(c, [[-9, 9], [9, -9]]);
		},
		revealed: (c) => {
			eye$1(c, true);
			line(c, [[-9, -9], [-5, -6]]);
			line(c, [[9, -9], [5, -6]]);
			line(c, [[0, -10], [0, -7]]);
		},
		overwatch: (c) => {
			circle(c, 0, 0, 7);
			line(c, [[0, -10], [0, -4]]);
			line(c, [[0, 4], [0, 10]]);
			line(c, [[-10, 0], [-4, 0]]);
			line(c, [[4, 0], [10, 0]]);
			circle(c, 0, 0, 1.8, true);
		},
		marked: (c) => {
			line(c, [[-7, -7], [7, 7]]);
			line(c, [[7, -7], [-7, 7]]);
			circle(c, 0, 0, 9);
		},
		time_bomb: (c) => {
			circle(c, -1, 2, 7, true);
			line(c, [[3, -4], [7, -9]]);
			c.fillStyle = "#fff";
			star$1(c, 8, -9, 3);
		},
		charging: (c) => {
			circle(c, 0, 0, 8);
			circle(c, 0, 0, 3.5, true);
		},
		shard_burst: (c) => {
			star$1(c, -4, -4, 4);
			star$1(c, 5, -2, 3);
			drop$1(c, 0, 5, 5);
		},
		sword_formation: (c) => {
			for (const x of [
				-6,
				0,
				6
			]) {
				line(c, [[x, -9], [x, 6]]);
				line(c, [[x - 2.5, 3], [x + 2.5, 3]]);
			}
		},
		array_ward: (c) => {
			circle(c, 0, 0, 8.5);
			circle(c, 0, 0, 3, true);
		},
		oath_bonus_easy: (c) => {
			star$1(c, 0, -2, 6);
			circle(c, 0, 8, 1.5, true);
		},
		oath_bonus_medium: (c) => {
			star$1(c, 0, -2, 6);
			circle(c, -3, 8, 1.5, true);
			circle(c, 3, 8, 1.5, true);
		},
		oath_bonus_hard: (c) => {
			star$1(c, 0, -2, 6);
			for (const x of [
				-5,
				0,
				5
			]) circle(c, x, 8, 1.5, true);
		},
		oath_broken: (c) => {
			star$1(c, 0, 0, 6);
			line(c, [[-8, 8], [8, -8]]);
		},
		summit_array_ward: (c) => {
			circle(c, 0, 0, 8.5);
			circle(c, 0, 0, 5);
			circle(c, 0, 0, 2, true);
		},
		mist_return: (c) => {
			circle(c, 0, 2, 7.5);
			drop$1(c, 0, -2, 5);
		},
		league_truce: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [[-3, -4.5], [-3, 4.5]]);
			line(c, [[3, -4.5], [3, 4.5]]);
		},
		rift_resonance: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [
				[0, -6],
				[4, 0],
				[0, 6],
				[-4, 0],
				[0, -6]
			]);
		},
		rift_channel: (c) => {
			line(c, [
				[0, -5],
				[3.5, 0],
				[0, 5],
				[-3.5, 0],
				[0, -5]
			]);
			line(c, [[0, -6.5], [0, -9.5]]);
			line(c, [[-5, 4], [-8, 6.5]]);
			line(c, [[5, 4], [8, 6.5]]);
		},
		crystal_surge: (c) => {
			line(c, [
				[0, -8],
				[5, -1],
				[0, 6],
				[-5, -1],
				[0, -8]
			]);
			circle(c, 0, 9, 1.5, true);
		},
		crystal_surge_2: (c) => {
			line(c, [
				[0, -8],
				[5, -1],
				[0, 6],
				[-5, -1],
				[0, -8]
			]);
			circle(c, -3, 9, 1.5, true);
			circle(c, 3, 9, 1.5, true);
		},
		rift_collapse: (c) => {
			line(c, [
				[-1, -8],
				[-6, 0],
				[-1, 8]
			]);
			line(c, [
				[1, -8],
				[6, 0],
				[1, 8]
			]);
			line(c, [
				[0, -6],
				[2, -1],
				[-2, 2],
				[0, 6]
			]);
		},
		molten_burst: (c) => {
			star$1(c, -5, -4, 3.5);
			star$1(c, 5, -4, 3.5);
			flame(c, 0, 4, 7);
		},
		heart_ember_burst: (c) => {
			line(c, [
				[-8, -2],
				[-5, -7],
				[0, -8.5],
				[5, -7],
				[8, -2]
			]);
			star$1(c, 0, -3, 3);
			flame(c, 0, 4, 7);
		},
		frost_ember_burst: (c) => {
			star$1(c, -5, -5, 3.5);
			star$1(c, 5, -5, 3.5);
			for (let i = 0; i < 3; i++) {
				const a = i / 3 * Math.PI;
				line(c, [[Math.cos(a) * -5, 4 + Math.sin(a) * -5], [Math.cos(a) * 5, 4 + Math.sin(a) * 5]]);
			}
		},
		molten_shell: (c) => {
			circle(c, 0, 0, 8.5);
			flame(c, 0, 2, 7);
		},
		hard_shell: (c) => {
			line(c, [
				[-8, 4],
				[-5, -4],
				[0, -7],
				[5, -4],
				[8, 4]
			]);
			line(c, [
				[-5, 6],
				[-3, 0],
				[0, -2],
				[3, 0],
				[5, 6]
			]);
		},
		heart_link: (c) => {
			circle(c, -5, 0, 4);
			circle(c, 5, 0, 4);
			line(c, [[-1, 0], [1, 0]]);
		},
		slow: (c) => {
			circle(c, 0, 0, 8.5);
			line(c, [[0, 0], [0, -6]]);
			line(c, [[0, 0], [4, 3]]);
		},
		root: (c) => {
			line(c, [[0, -9], [0, 4]]);
			line(c, [[0, 4], [-7, 9]]);
			line(c, [[0, 4], [7, 9]]);
			line(c, [[0, 1], [-5, -3]]);
		},
		stun: (c) => {
			star$1(c, -5, -3, 5);
			star$1(c, 5, -3, 5);
			star$1(c, 0, 5, 5);
		},
		frozen: (c) => {
			for (let i = 0; i < 3; i++) {
				const a = i / 3 * Math.PI;
				line(c, [[Math.cos(a) * -10, Math.sin(a) * -10], [Math.cos(a) * 10, Math.sin(a) * 10]]);
			}
			circle(c, 0, 0, 2.5, true);
		},
		weaken: (c) => {
			sword(c);
			arrow$1(c, 6, 3, false);
		},
		empowered: (c) => {
			line(c, [
				[-8, 0],
				[0, -8],
				[8, 0]
			]);
			line(c, [
				[-8, 8],
				[0, 0],
				[8, 8]
			]);
		},
		commanding: (c) => {
			line(c, [[-9, 9], [-1, -1]]);
			circle(c, -3, -5, 2.4, true);
			circle(c, 3, 5, 3.5);
			arrow$1(c, 8, -3, true);
		},
		infused_fire: (c) => {
			sword(c);
			circle(c, 7, -7, 2.8, true);
			circle(c, -7, 7, 1.6, true);
		},
		infused_holy: (c) => {
			sword(c);
			line(c, [[7, -10], [7, -4]]);
			line(c, [[4, -7], [10, -7]]);
		},
		race_adapt: (c) => {
			line(c, [[-9, 0], [7, 0]]);
			line(c, [
				[2, -6],
				[8, 0],
				[2, 6]
			]);
			line(c, [[-9, -6], [-4, -6]]);
			line(c, [[-9, 6], [-4, 6]]);
		},
		race_stonewall: (c) => {
			shield(c);
			line(c, [[-6, 8], [6, 8]]);
			line(c, [[-3, 5], [3, 5]]);
		},
		rallied: (c) => {
			line(c, [[-6, 10], [-6, -9]]);
			c.beginPath();
			c.moveTo(-6, -9);
			c.lineTo(8, -5);
			c.lineTo(-6, -1);
			c.closePath();
			c.fill();
		},
		vulnerable: (c) => {
			shield(c);
			line(c, [
				[-2, -8],
				[2, -2],
				[-2, 2],
				[2, 9]
			]);
		},
		entangled: (c) => {
			c.beginPath();
			c.moveTo(-9, -6);
			c.bezierCurveTo(-2, -12, 6, -2, -1, 0);
			c.bezierCurveTo(-8, 2, 0, 8, 9, 2);
			c.stroke();
			arrow$1(c, -5, 5, false);
		},
		armor_broken: (c) => {
			c.beginPath();
			c.moveTo(-8, -6);
			c.lineTo(0, -9);
			c.lineTo(8, -6);
			c.lineTo(8, 1);
			c.lineTo(0, 9);
			c.lineTo(-8, 1);
			c.closePath();
			c.stroke();
			arrow$1(c, 0, 0, false);
		},
		hasted: (c) => {
			line(c, [
				[-8, -7],
				[-1, 0],
				[-8, 7]
			]);
			line(c, [
				[1, -7],
				[8, 0],
				[1, 7]
			]);
		},
		regenerating: (c) => {
			c.fillRect(-2.5, -9, 5, 18);
			c.fillRect(-9, -2.5, 18, 5);
		},
		undying: (c) => {
			c.beginPath();
			c.moveTo(0, 9);
			c.bezierCurveTo(-12, 0, -6, -10, 0, -4);
			c.bezierCurveTo(6, -10, 12, 0, 0, 9);
			c.fill();
			c.fillStyle = "#000";
			c.fillRect(-1, -4, 2, 9);
			c.fillRect(-3.5, -1.5, 7, 2);
		},
		soul_link: (c) => {
			circle(c, -4, 0, 5.5);
			circle(c, 4, 0, 5.5);
		},
		taunted: (c) => {
			circle(c, 0, 0, 9);
			circle(c, 0, 0, 4.5);
			circle(c, 0, 0, 1.5, true);
		},
		feared: (c) => {
			c.font = `bold 17px ${FONT}`;
			c.textAlign = "center";
			c.textBaseline = "middle";
			c.fillText("!", 0, 1);
			line(c, [[-8, -6], [-5, -3]]);
			line(c, [[8, -6], [5, -3]]);
		},
		overdrawn: (c) => {
			c.beginPath();
			c.roundRect(-8, -6, 14, 12, 2);
			c.stroke();
			line(c, [
				[6, -2],
				[9, -2],
				[9, 2],
				[6, 2]
			]);
			arrow$1(c, -1, 0, false);
		},
		silenced: (c) => {
			c.beginPath();
			c.roundRect(-9, -7, 18, 12, 4);
			c.stroke();
			c.beginPath();
			c.moveTo(-3, 5);
			c.lineTo(-6, 10);
			c.lineTo(2, 5);
			c.stroke();
			line(c, [[-10, 9], [10, -9]]);
		},
		blinded: (c) => {
			eye$1(c, false);
			line(c, [[-9, 7], [9, -7]]);
		},
		stance_fury: (c) => {
			for (const dx of [
				-5,
				0,
				5
			]) line(c, [[dx - 3, 8], [dx + 3, -8]]);
		},
		stance_bulwark: (c) => {
			c.fillRect(-8, -2, 16, 10);
			for (const dx of [
				-8,
				-2,
				4
			]) c.fillRect(dx, -7, 4, 5);
		},
		stance_guard: (c) => {
			c.beginPath();
			c.moveTo(-8, -8);
			c.lineTo(8, -8);
			c.lineTo(8, 1);
			c.lineTo(0, 10);
			c.lineTo(-8, 1);
			c.closePath();
			c.stroke();
		},
		stance_bastion: (c) => {
			c.strokeRect(-9, -8, 18, 16);
			line(c, [[-9, -2], [9, -2]]);
			line(c, [[-9, 4], [9, 4]]);
			line(c, [[0, -8], [0, -2]]);
		},
		stance_ironwall: (c) => {
			c.strokeRect(-9, -7, 18, 14);
			line(c, [[-9, 0], [9, 0]]);
			line(c, [[-3, -7], [-3, 0]]);
			line(c, [[3, 0], [3, 7]]);
		},
		stance_flame: (c) => {
			line(c, [[-7, 8], [7, -8]]);
			line(c, [[-9, 3], [-3, 9]]);
			c.beginPath();
			c.arc(7, 6, 3, 0, TAU$1);
			c.fill();
		},
		stance_blaze: (c) => {
			c.beginPath();
			c.moveTo(0, -10);
			c.quadraticCurveTo(9, -1, 6, 6);
			c.quadraticCurveTo(0, 12, -6, 6);
			c.quadraticCurveTo(-8, 0, -2, -4);
			c.quadraticCurveTo(-1, -7, 0, -10);
			c.closePath();
			c.stroke();
		},
		stance_frost: (c) => {
			line(c, [[-7, 8], [7, -8]]);
			line(c, [[3, 4], [9, 4]]);
			line(c, [[6, 1], [6, 7]]);
		},
		stance_glacier: (c) => {
			for (const [x, y] of [
				[0, 9],
				[8, 4.5],
				[8, -4.5]
			]) line(c, [[-x, -y], [x, y]]);
		}
	};
	/** 在以 (0,0) 為中心、半徑約 10 的範圍畫狀態圖樣（顏色與線寬由呼叫端設）；不認得的狀態畫名稱第一個字。 */
	function drawGlyph(c, id) {
		const known = id == null ? void 0 : GLYPH[id];
		if (known !== void 0) {
			known(c);
			return;
		}
		const name = id == null || id === "" ? "?" : statusName(id);
		c.font = `bold 13px ${FONT}`;
		c.textAlign = "center";
		c.textBaseline = "middle";
		c.fillText([...name][0] ?? "?", 0, 1);
	}
	//#endregion
	//#region F:/PythonProject/LLM-MMO-TRPG/.claude/worktrees/eager-gauss-b843fa/client/src/render/skillParts.ts
	var TAU = Math.PI * 2;
	function arrow(ctx, x0, y0, x1, y1, head = 4) {
		const a = Math.atan2(y1 - y0, x1 - x0);
		ctx.beginPath();
		ctx.moveTo(x0, y0);
		ctx.lineTo(x1, y1);
		ctx.stroke();
		ctx.beginPath();
		ctx.moveTo(x1 + Math.cos(a), y1 + Math.sin(a));
		ctx.lineTo(x1 - Math.cos(a - .6) * head, y1 - Math.sin(a - .6) * head);
		ctx.lineTo(x1 - Math.cos(a + .6) * head, y1 - Math.sin(a + .6) * head);
		ctx.closePath();
		ctx.fill();
	}
	function dot(ctx, x, y, r) {
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU);
		ctx.fill();
	}
	function ring(ctx, x, y, r) {
		ctx.beginPath();
		ctx.arc(x, y, r, 0, TAU);
		ctx.stroke();
	}
	/** 符文：菱形外框，裡面一個小菱形（`filled` 時填滿）。 */
	function runeMark(ctx, x, y, k = 1, filled = false) {
		const r = 8 * k;
		ctx.beginPath();
		ctx.moveTo(x, y - r);
		ctx.lineTo(x + r, y);
		ctx.lineTo(x, y + r);
		ctx.lineTo(x - r, y);
		ctx.closePath();
		ctx.stroke();
		const s = 3.6 * k;
		ctx.beginPath();
		ctx.moveTo(x, y - s);
		ctx.lineTo(x + s, y);
		ctx.lineTo(x, y + s);
		ctx.lineTo(x - s, y);
		ctx.closePath();
		if (filled) ctx.fill();
		else ctx.stroke();
	}
	function person(ctx, x, y, k = 1) {
		dot(ctx, x, y - 5 * k, 2.6 * k);
		ctx.beginPath();
		ctx.moveTo(x - 4.5 * k, y + 5 * k);
		ctx.quadraticCurveTo(x - 4.5 * k, y - 1.5 * k, x, y - 1.5 * k);
		ctx.quadraticCurveTo(x + 4.5 * k, y - 1.5 * k, x + 4.5 * k, y + 5 * k);
		ctx.closePath();
		ctx.fill();
	}
	function shieldPath(ctx, k = 1) {
		ctx.beginPath();
		ctx.moveTo(0, -9 * k);
		ctx.lineTo(7.5 * k, -6 * k);
		ctx.lineTo(7 * k, 2 * k);
		ctx.lineTo(0, 9 * k);
		ctx.lineTo(-7 * k, 2 * k);
		ctx.lineTo(-7.5 * k, -6 * k);
		ctx.closePath();
	}
	function heart(ctx, k = 1) {
		ctx.beginPath();
		ctx.moveTo(0, 8 * k);
		ctx.bezierCurveTo(-11 * k, 0, -6 * k, -10 * k, 0, -4 * k);
		ctx.bezierCurveTo(6 * k, -10 * k, 11 * k, 0, 0, 8 * k);
		ctx.closePath();
	}
	function drop(ctx, x, y, k = 1) {
		ctx.beginPath();
		ctx.moveTo(x, y - 8 * k);
		ctx.bezierCurveTo(x + 6.5 * k, y, x + 5.5 * k, y + 6 * k, x, y + 6 * k);
		ctx.bezierCurveTo(x - 5.5 * k, y + 6 * k, x - 6.5 * k, y, x, y - 8 * k);
		ctx.fill();
	}
	function hourglass(ctx) {
		ctx.beginPath();
		ctx.moveTo(-6, -8);
		ctx.lineTo(6, -8);
		ctx.lineTo(0, 0);
		ctx.lineTo(6, 8);
		ctx.lineTo(-6, 8);
		ctx.lineTo(0, 0);
		ctx.closePath();
		ctx.fill();
	}
	function text(ctx, s, size = 11) {
		ctx.font = `700 ${size}px ${FONT}`;
		ctx.textAlign = "center";
		ctx.textBaseline = "middle";
		ctx.fillText(s, 0, .5);
	}
	function eye(ctx, slashed) {
		ctx.beginPath();
		ctx.moveTo(-9, 0);
		ctx.quadraticCurveTo(0, -9, 9, 0);
		ctx.quadraticCurveTo(0, 9, -9, 0);
		ctx.stroke();
		dot(ctx, 0, 0, 2.6);
		if (slashed) {
			ctx.beginPath();
			ctx.moveTo(-8, 7);
			ctx.lineTo(8, -7);
			ctx.stroke();
		}
	}
	function footprints(ctx) {
		for (const [x, y, r] of [[
			-4,
			4,
			-.3
		], [
			3,
			-3,
			.3
		]]) {
			ctx.save();
			ctx.translate(x, y);
			ctx.rotate(r);
			ctx.beginPath();
			ctx.ellipse(0, 0, 2.6, 4, 0, 0, TAU);
			ctx.fill();
			dot(ctx, 0, -5.5, 1.3);
			ctx.restore();
		}
	}
	function chevrons(ctx, dir) {
		for (const o of [-4, 2]) {
			ctx.beginPath();
			if (dir === "right") {
				ctx.moveTo(o - 2, -6);
				ctx.lineTo(o + 4, 0);
				ctx.lineTo(o - 2, 6);
			} else {
				ctx.moveTo(-6, -o + 2);
				ctx.lineTo(0, -o - 4);
				ctx.lineTo(6, -o + 2);
			}
			ctx.stroke();
		}
	}
	function dice(ctx) {
		ctx.beginPath();
		ctx.roundRect(-7.5, -7.5, 15, 15, 3);
		ctx.stroke();
		for (const [x, y] of [
			[-3.5, -3.5],
			[3.5, 3.5],
			[0, 0],
			[3.5, -3.5],
			[-3.5, 3.5]
		]) dot(ctx, x, y, 1.4);
	}
	function card(ctx, x, y) {
		ctx.beginPath();
		ctx.roundRect(x - 4.5, y - 6.5, 9, 13, 1.5);
		ctx.fill();
	}
	function star(ctx, n, ro, ri) {
		starPath(ctx, 0, 0, n, ro, ri);
		ctx.fill();
	}
	function plus(ctx, x, y) {
		ctx.fillRect(x - 1, y - 3.5, 2, 7);
		ctx.fillRect(x - 3.5, y - 1, 7, 2);
	}
	function ghost(ctx, alpha, draw) {
		const before = ctx.globalAlpha;
		ctx.globalAlpha = before * alpha;
		draw();
		ctx.globalAlpha = before;
	}
	/** 圖樣表（id → [預設色, 畫法]）；顏色以 `statusColor` 為準，這裡的色只給少數不經 `statusColor` 的舊用法。 */
	var STATUS = Object.fromEntries(Object.entries(GLYPH).map(([id, draw]) => [id, ["#d8d8e0", draw]]));
	var UNKNOWN_COLOR = "#d8d8e0";
	/** 狀態圖樣（技能部件、組裝列用；不認得的狀態畫名稱第一個字）。 */
	function statusGlyph(ctx, id) {
		drawGlyph(ctx, id);
	}
	hooks.status = (c, _o, id) => {
		c.save();
		c.fillStyle = c.strokeStyle = statusColor(id);
		c.lineWidth = 2.2;
		c.lineCap = c.lineJoin = "round";
		statusGlyph(c, id);
		c.restore();
	};
	/** 狀態的圖樣顏色：`control_group` → 持續傷害元素 → 專屬色 → `polarity`（見 `statusIcon.glyphColor`）。 */
	function statusColor(id) {
		if (id == null || id === "") return UNKNOWN_COLOR;
		return glyphColor(id);
	}
	var surfaceColor = (id) => id == null ? "#c8c8c8" : SURFACE_ICON_COLOR[id] ?? "#c8c8c8";
	function surfaceGlyph(ctx, id) {
		ctx.save();
		ctx.fillStyle = surfaceColor(id);
		drop(ctx, 0, -2, .9);
		ctx.globalAlpha = .85;
		ctx.beginPath();
		ctx.ellipse(0, 7, 9, 2.6, 0, 0, TAU);
		ctx.fill();
		ctx.restore();
	}
	var stackDots = (c) => {
		for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 3, 2.4);
	};
	var EFFECT = {
		damage: ["#ffffff", (c) => star(c, 8, 9.5, 4)],
		heal: ["#7cf29a", (c) => {
			c.fillRect(-2.5, -8, 5, 16);
			c.fillRect(-8, -2.5, 16, 5);
		}],
		shield: ["#8fd0ff", (c) => {
			shieldPath(c);
			c.fill();
		}],
		cleanse: ["#bfffe8", (c) => star(c, 4, 9, 2.4)],
		push: ["#ffffff", (c) => {
			dot(c, -6, 0, 3.4);
			arrow(c, -1, 0, 9, 0, 4.5);
		}],
		pull: ["#ffffff", (c) => {
			dot(c, -7, 0, 3.4);
			arrow(c, 9, 0, -1, 0, 4.5);
		}],
		knock_prone: ["#e0c49a", (c) => STATUS["prone"][1](c)],
		shockwave: ["#e0c49a", (c) => {
			STATUS["prone"][1](c);
			c.beginPath();
			c.moveTo(-10, 11);
			c.lineTo(-6, 9);
			c.lineTo(-2, 11);
			c.lineTo(2, 9);
			c.lineTo(6, 11);
			c.lineTo(10, 9);
			c.stroke();
		}],
		teleport: ["#d8b8ff", (c) => {
			c.setLineDash([2.5, 2]);
			ring(c, -3, 2, 6);
			c.setLineDash([]);
			dot(c, 5, -4, 3.2);
		}],
		dash: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-9, -4);
			c.lineTo(-1, -4);
			c.moveTo(-9, 4);
			c.lineTo(-1, 4);
			c.stroke();
			arrow(c, -3, 0, 9, 0, 4.5);
		}],
		charge_through: ["#ffffff", (c) => {
			c.fillRect(-1.5, -9, 3, 18);
			arrow(c, -9, 0, 9, 0, 4.5);
		}],
		shadowstep: ["#c8a0ff", (c) => {
			c.beginPath();
			c.arc(-2, 0, 7, .6, TAU - .6);
			c.stroke();
			arrow(c, 0, 0, 9, 0, 4);
		}],
		leap: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-9, 6);
			c.quadraticCurveTo(0, -14, 7, 4);
			c.stroke();
			arrow(c, 5, 0, 8, 6, 4);
		}],
		swap: ["#ffffff", (c) => {
			arrow(c, -8, -3, 8, -3, 3.5);
			arrow(c, 8, 3, -8, 3, 3.5);
		}],
		apply_status: ["#ffffff", (c) => ring(c, 0, 0, 7)],
		create_surface: ["#ffffff", (c) => surfaceGlyph(c, null)],
		blow_surface: ["#cfe8ff", (c) => {
			surfaceGlyph(c, null);
			arrow(c, -9, -7, 8, -7, 3.5);
		}],
		enter_form: ["#c9a0ff", (c) => {
			person(c, -6, 0, .8);
			arrow(c, -1, 0, 6, 0, 3);
			dot(c, 8, 0, 2);
		}],
		leave_form: ["#c9a0ff", (c) => {
			dot(c, -8, 0, 2);
			arrow(c, 1, 0, -6, 0, 3);
			person(c, 6, 0, .8);
		}],
		clear_surface: ["#cfe8ff", (c) => {
			surfaceGlyph(c, null);
			c.beginPath();
			c.moveTo(-8, 8);
			c.lineTo(8, -8);
			c.stroke();
		}],
		destroy_object: ["#e0c49a", (c) => {
			c.strokeRect(-7, -7, 14, 14);
			c.beginPath();
			c.moveTo(-2, -7);
			c.lineTo(1, -1);
			c.lineTo(-2, 3);
			c.lineTo(1, 7);
			c.stroke();
		}],
		create_obstacle: ["#d8c0a0", (c) => {
			for (let r = 0; r < 3; r++) for (let i = 0; i < 2; i++) c.fillRect(-8 + i * 8 + r % 2 * 4 - (r % 2 === 1 && i === 1 ? 4 : 0), -7 + r * 5, 7, 4);
		}],
		raise_terrain: ["#e0c49a", (c) => {
			c.fillRect(-8, 2, 16, 6);
			arrow(c, 0, 1, 0, -9, 4);
		}],
		lower_terrain: ["#e0c49a", (c) => {
			c.fillRect(-8, 2, 16, 6);
			arrow(c, 0, -9, 0, 0, 4);
		}],
		intercept: ["#8fd0ff", (c) => {
			person(c, -3, 1, 1.1);
			c.save();
			c.translate(5, 0);
			shieldPath(c, .6);
			c.fill();
			c.restore();
		}],
		add_stack: ["#ffd04a", (c) => {
			stackDots(c);
			c.fillRect(-1, -9, 2, 7);
			c.fillRect(-3.5, -6.5, 7, 2);
		}],
		consume_stack: ["#ffd04a", (c) => {
			stackDots(c);
			c.fillRect(-3.5, -6.5, 7, 2);
		}],
		consume_status: ["#ffb03a", (c) => {
			star(c, 6, 9, 4.5);
			c.save();
			c.fillStyle = "#1a1420";
			dot(c, 0, 0, 2.6);
			c.restore();
		}],
		place_trap: ["#e0e0e0", (c) => {
			for (const [b, t] of [[-2, -8], [2, 8]]) {
				c.beginPath();
				c.moveTo(-8, b);
				for (let i = 0; i < 4; i++) {
					c.lineTo(-8 + i * 4 + 2, t * .6 + b * .4);
					c.lineTo(-8 + (i + 1) * 4, b);
				}
				c.closePath();
				c.fill();
			}
		}],
		grant_ap: ["#ffe14d", (c) => {
			ring(c, -2, 0, 6.5);
			text(c, "+", 12);
		}],
		reset_cooldown: ["#a8e0ff", (c) => {
			c.beginPath();
			c.arc(0, 0, 7.5, -1.2, 4.2);
			c.stroke();
			arrow(c, -6.5, -4, -3.5, -8, 3.5);
		}],
		cheat_death: ["#ff7a7a", (c) => {
			heart(c);
			c.fill();
		}],
		redirect_damage: ["#ffffff", (c) => {
			c.beginPath();
			c.moveTo(-8, 7);
			c.lineTo(0, -1);
			c.stroke();
			arrow(c, 0, -1, 8, 7, 4);
		}],
		copy_skill: ["#d8c8ff", (c) => {
			ghost(c, .6, () => card(c, -3, -2));
			card(c, 3, 2);
		}],
		extra_reaction: ["#8fd0ff", (c) => {
			shieldPath(c, .9);
			c.stroke();
			elementGlyph(c, "lightning", 0, 0, .55, c.fillStyle);
		}],
		hurl_object: ["#e0b080", (c) => {
			c.fillRect(-9, 1, 7, 7);
			c.beginPath();
			c.moveTo(-5, 0);
			c.quadraticCurveTo(0, -12, 7, 2);
			c.stroke();
			arrow(c, 5, -2, 8, 4, 3.5);
		}],
		topple: ["#c8c0b0", (c) => {
			c.save();
			c.rotate(.6);
			c.fillRect(-2.5, -9, 5, 16);
			c.restore();
			c.fillRect(-9, 7, 18, 2);
		}],
		restore_resource: ["#c89cff", (c) => {
			c.beginPath();
			c.moveTo(-2, -8);
			c.lineTo(4, -2);
			c.lineTo(-2, 4);
			c.lineTo(-8, -2);
			c.closePath();
			c.fill();
			c.fillRect(4, 2, 2, 7);
			c.fillRect(1.5, 4.5, 7, 2);
		}],
		steal_buff: ["#c8a0ff", (c) => {
			c.beginPath();
			c.moveTo(-8, 6);
			c.lineTo(-8, -2);
			c.quadraticCurveTo(-8, -8, -2, -8);
			c.lineTo(6, -8);
			c.stroke();
			chevrons(c, "up");
		}],
		dispel: ["#d8d0ff", (c) => {
			c.beginPath();
			c.moveTo(-7, -7);
			c.lineTo(7, 7);
			c.moveTo(7, -7);
			c.lineTo(-7, 7);
			c.stroke();
		}],
		reveal: ["#ffffff", (c) => eye(c, false)],
		revive: ["#ffd75e", (c) => {
			heart(c);
			c.fill();
			c.save();
			c.fillStyle = "#1a1420";
			c.fillRect(-1.2, -4, 2.4, 8);
			c.fillRect(-4, -1.2, 8, 2.4);
			c.restore();
		}],
		delayed_damage: ["#ffb03a", (c) => {
			c.save();
			c.scale(.75, .75);
			c.translate(-4, 0);
			hourglass(c);
			c.restore();
			c.save();
			c.translate(5, -3);
			star(c, 6, 5, 2.4);
			c.restore();
		}],
		summon: ["#8ff0e2", (c) => {
			person(c, -2, 1, 1.25);
			plus(c, 6, -5);
		}],
		zone: ["#ffd04a", (c) => {
			c.setLineDash([3, 2]);
			ring(c, 0, 0, 8);
			c.setLineDash([]);
			dot(c, 0, 0, 2.5);
		}],
		rule_change: ["#ffd75e", (c) => {
			c.beginPath();
			c.roundRect(-7, -8, 14, 16, 2);
			c.stroke();
			c.fillRect(-4, -4, 8, 1.6);
			c.fillRect(-4, 0, 8, 1.6);
			c.fillRect(-4, 4, 5, 1.6);
		}],
		gamble: ["#ffffff", dice],
		grant_skill: ["#d8c8ff", (c) => {
			card(c, -2, 1);
			plus(c, 6, -5);
		}],
		sacrifice_summon: ["#ff9f6b", (c) => {
			person(c, 0, 1, .9);
			arrow(c, 0, -6, 0, -10.5, 3);
			arrow(c, -6, 0, -10.5, 0, 3);
			arrow(c, 6, 0, 10.5, 0, 3);
		}],
		inscribe: ["#ffe08a", (c) => runeMark(c, 0, 0, 1.1, true)],
		detonate_runes: ["#ffb36b", (c) => {
			runeMark(c, 0, 0, .6, true);
			arrow(c, 0, -5, 0, -10, 3);
			arrow(c, 0, 5, 0, 10, 3);
			arrow(c, -5, 0, -10, 0, 3);
			arrow(c, 5, 0, 10, 0, 3);
		}]
	};
	EFFECT["teleport_target"] = EFFECT["swap"];
	EFFECT["swap_any"] = EFFECT["swap"];
	EFFECT["consume_stack"][1];
	({
		on_hit: EFFECT["damage"][1],
		on_kill: (c) => {
			dot(c, 0, -2, 7);
			c.fillRect(-4, 2, 8, 6);
			c.save();
			c.fillStyle = "#1a1420";
			dot(c, -2.8, -2, 2);
			dot(c, 2.8, -2, 2);
			c.restore();
		},
		on_crit: (c) => star(c, 4, 10, 2.6),
		on_natural_20: (c) => {
			c.beginPath();
			for (let i = 0; i < 6; i++) c.lineTo(Math.cos(i / 6 * TAU - Math.PI / 2) * 9.5, Math.sin(i / 6 * TAU - Math.PI / 2) * 9.5);
			c.closePath();
			c.stroke();
			text(c, "20", 8);
		},
		on_move: footprints,
		on_damaged: STATUS["vulnerable"][1],
		on_status_applied: (c) => {
			ring(c, 0, 0, 8);
			dot(c, 0, 0, 3);
		},
		on_cast_tag: (c) => card(c, 0, 0),
		on_collision: (c) => {
			arrow(c, -9, 0, -2, 0, 3.5);
			arrow(c, 9, 0, 2, 0, 3.5);
		},
		on_turn_start: (c) => {
			c.beginPath();
			c.arc(0, 4, 7, Math.PI, 0);
			c.fill();
			c.fillRect(-10, 4, 20, 1.8);
			arrow(c, 0, -2, 0, -9, 3);
		},
		on_turn_end: (c) => {
			c.beginPath();
			c.arc(0, 4, 7, Math.PI, 0);
			c.fill();
			c.fillRect(-10, 4, 20, 1.8);
			arrow(c, 0, -10, 0, -3, 3);
		},
		on_enter_surface: (c) => drop(c, 0, 0, .9),
		on_summon_downed: (c) => {
			ring(c, 0, -2, 6);
			dot(c, 0, -2, 2.4);
			arrow(c, 0, 5, 0, 10, 3);
		},
		every_n_hits: (c) => {
			for (let i = 0; i < 3; i++) dot(c, -6 + i * 6, 0, 2.6);
		},
		enemy_enters_adjacent: (c) => {
			ring(c, 2, 0, 6);
			arrow(c, -10, 0, -3, 0, 3.5);
		},
		enemy_leaves_adjacent: (c) => {
			ring(c, -2, 0, 6);
			arrow(c, 2, 0, 10, 0, 3.5);
		},
		hit_by_spell: (c) => {
			shieldPath(c);
			c.stroke();
			c.save();
			c.scale(.5, .5);
			star(c, 5, 9, 4);
			c.restore();
		},
		hit_by_attack: (c) => {
			shieldPath(c);
			c.stroke();
			c.beginPath();
			c.moveTo(-9, -9);
			c.lineTo(-2, -2);
			c.stroke();
		},
		hit_by_melee: (c) => {
			shieldPath(c);
			c.stroke();
			c.beginPath();
			c.moveTo(-9, -9);
			c.lineTo(-2, -2);
			c.moveTo(-9, -4);
			c.lineTo(-5, -8);
			c.stroke();
		},
		ally_targeted: (c) => {
			person(c, 0, 1, 1.1);
			ghost(c, .9, () => STATUS["marked"][1](c));
		},
		ally_downed: STATUS["prone"][1],
		ally_hit_adjacent: (c) => {
			person(c, -4, 1, .9);
			c.save();
			c.translate(5, -3);
			star(c, 6, 5, 2.2);
			c.restore();
		}
	})["on_kill"];
	[...Object.keys(EFFECT$1), ...Object.keys(EFFECT_ALIAS)], Object.keys(STATUS), Object.keys(SURFACE), Object.keys(COND), [...Object.keys(TRIG$1), ...Object.keys(TRIG_ALIAS)], Object.keys(LINK$1), Object.keys(COST);
	Object.fromEntries(Object.entries(SHAPE_NAMES).map(([zh, id]) => [id, zh]));
	var CACHE_LIMIT = 300;
	var cardCache = /* @__PURE__ */ new Map();
	/** 卡片小圖的快取鍵。 */
	var cardGlyphKey = (id, px, res = 2, opt = {}) => [
		id,
		px,
		res,
		opt.tint?.join("+") ?? "",
		opt.pinned === false ? "off" : "on"
	].join("|");
	/** 技能卡小圖（常駐行 16、效果行 18、圖釘 13）的離屏 canvas：`QP.cardCanvas`（圖樣撐滿整格、整數裝置像素貼上）。 */
	function cardGlyphCanvas(id, px, res = 2, opt = {}) {
		const key = cardGlyphKey(id, px, res, opt);
		const hit = cardCache.get(key);
		if (hit !== void 0) return hit;
		const canvas = cardCanvas(id, px, 1, {
			res,
			...opt.tint == null ? {} : { tint: opt.tint },
			...opt.pinned === void 0 ? {} : { pinned: opt.pinned }
		});
		if (cardCache.size >= CACHE_LIMIT) {
			const oldest = cardCache.keys().next().value;
			if (oldest !== void 0) cardCache.delete(oldest);
		}
		cardCache.set(key, canvas);
		return canvas;
	}
	//#endregion
	//#region entry.tsx
	var svgOf = (el) => {
		const s = (0, import_server_browser.renderToStaticMarkup)(el);
		const m = /<svg[\s\S]*<\/svg>/.exec(s);
		return m ? m[0] : s;
	};
	window.QHudLive = {
		HUD_BAR_ORDER,
		HUD_BACKING,
		HUD_BACKING_EDGE,
		HUD_BACKING_R,
		CREST_REGIONS,
		hudBarName,
		bar: (k, size) => svgOf((0, import_react.createElement)(HudBarIcon, {
			k,
			size
		})),
		hud: (name, size) => svgOf((0, import_react.createElement)(HudIcon, {
			name,
			size
		})),
		tool: (name, size) => svgOf((0, import_react.createElement)(BattleToolIcon, {
			name,
			size
		})),
		settings: (icon) => svgOf((0, import_react.createElement)(SettingsHead, {
			icon,
			children: "x"
		})),
		crest: (region, size) => svgOf((0, import_react.createElement)(RegionCrest, {
			region,
			size
		})),
		accent: (region) => regionThemeFor(region).accent,
		cardGlyphCanvas
	};
	//#endregion
})();
