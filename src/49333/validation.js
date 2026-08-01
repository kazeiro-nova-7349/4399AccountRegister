/**
 * @author : zhuxianda
 */

var regUser = new RegExp('^[\\w@]+$');
var regPasswd = new RegExp('^[\\w\\.(!@#$%&)]+$');
var regEmail = new RegExp('^[-\\w\\.]+@[-\\w\\.]+\\.[-\\w]+$');
var regQq = new RegExp('^[0-9]{4,11}$');
var regPhoneCaptcha = new RegExp('^[0-9]{4,6}$');
var regRealName = new RegExp(
    '^([\\u2E80-\\uFE4F·•]{2,30}|(?=[a-z]{2,}(\\s[a-z]+){1,2}).{2,30})$',
    'i'
);
var regPhone = new RegExp('^0?(13|14|15|16|17|18|19)[0-9]{9}$');

function encryptAES(IdVal) {
    return CryptoJS.AES.encrypt(IdVal, 'lzYW5qaXVqa').toString();
}
function replaceAll(originStr, oldStr, newStr) {
    return originStr.replace(new RegExp(oldStr, 'g'), newStr);
}

function __checkIdcard(a) {
    var b = /^\d{15}(\d{2}[\dx])?$/i;
    if (!b.test(a)) {
        return 0;
    }
    var c = a.length,
        d;
    if (c == 15) {
        d = '19' + a.substr(6, 6);
    } else {
        d = a.substr(6, 8);
    }
    if (
        (function (e) {
            var f = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
            var g = e.substr(0, 4) * 1;
            var h = e.substr(4, 2) * 1;
            var j = e.substr(6, 2) * 1;
            if (g < 1850 || g > 2050) {
                return 0;
            }
            if (g % 400 == 0 || (g % 4 == 0 && g % 100 != 0)) {
                f[1] = 29;
            }
            if (h < 1 || h > 12) {
                return 0;
            }
            if (j > f[h - 1] || j < 1) {
                return 0;
            }
            return 1;
        })(d) == 0
    ) {
        return 0;
    }
    if (c == 15) {
        return 0;
    }
    return (function (e) {
        var f = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2];
        var g = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2'];
        var h = 0;
        for (var j = 0; j < 17; j++) {
            h += parseInt(e.substr(j, 1)) * f[j];
        }
        h = g[h % 11];
        if (h == e.substr(17).toUpperCase()) {
            return 1;
        }
        return 0;
    })(a);
}

var Validaton = {
    lengthCheck: function (text, min, max) {
        // 判断长度
        var len = text.length;
        if ((len >= min) & (len <= max)) {
            return true;
        }
        return false;
    },

    // 判断用户名格式注册时是3~20个字符
    CheakUsername: function (username, isRegister) {
        if (username == '') return '请输入用户名';
        if (username == '请输入4399账号或手机号') return '请输入用户名';
        if (isRegister) {
            if (!this.lengthCheck(username, 3, 20)) return '用户名必须为 3-20 个字符';
            // if (username.indexOf("@") < 0) {
            // 	if (!this.lengthCheck(username, 3, 20))
            // 		return "用户名必须为 3-20 个字符";
            // } else if (!this.lengthCheck(username, 6, 30)) {
            // 	return "用户名必须为 6-30 个字符";
            // }
        } else if (!this.lengthCheck(username, 1, 25)) return '用户名必须为 1-25 个字符';
        if (isRegister) {
            var res = regUser.test(username);
            if (!res) return '只能包含字母/数字/“@”/“_”';
        }
        return '';
    },

    // 登录密码必须为2-20 个字符,注册密码必须为6-20 个字符
    CheakPWD: function (pwd, isRegister) {
        if (
            document.getElementById('j-idcanrd-name') != null &&
            document.getElementById('j-idcanrd-num') != null
        ) {
            document.getElementById('j-idcanrd-name').className = 'm_idcard_tip_view';
            document.getElementById('j-idcanrd-num').className = 'm_idcard_tip_view';
        }

        if (pwd == '') {
            return '请输入密码';
        }
        len = isRegister ? 6 : 2;
        if (!this.lengthCheck(pwd, len, 20)) {
            return '密码应为' + len + '-20 个字符';
        }
        if (isRegister) {
            var res = regPasswd.test(pwd);
            if (!res) return '密码有特殊字符';
            if (/^\d+$/.test(pwd)) return '请勿使用纯数字';
            if (/^[a-z]+$/.test(pwd)) return '请勿使用纯小写字母';
            if (/^[A-Z]+$/.test(pwd)) return '请勿使用纯大写字母';
        }

        return '';
    },

    // 当出现验证码时必须为不空，且只能4个字符
    CheakCaptcha: function (captcha) {
        if (captcha == '' || captcha == '点图片换一张') return '验证码不能为空';
        if (!this.lengthCheck(captcha, 4, 6)) return '验证码错误';
        return '';
    },

    CheckPhone: function (phone) {
        if (phone == '') {
            return '请输入有效的手机号码';
        }
        var res = regPhone.test(phone);
        if (!res) {
            return '请输入有效的手机号码';
        }
    },

    CheckEmail: function (email) {
        if (email == '') {
            //return "请输入QQ号"
            return '';
        }
        //var res = regEmail.test(email);
        //if(res)
        //	return "";
        var res = regQq.test(email);
        if (!res) {
            //return "";
            return 'QQ号无效，请重新输入';
        }
        //return "QQ号无效，请重新输入";
    },

    CheckRealname: function (realname, errTip) {
        if (realname == '') {
            return -1;
            //return "例如：" + errTip;
        }
        var res = regRealName.test(realname);
        if (res) {
            return '';
        }
        return '姓名无效，请重新输入';
    },

    CheckIdcard: function (idcard, errTip) {
        if (idcard == '') {
            return -1;
            //return "例如：" + errTip;
        } /*else if(idcard == "440106198101010155"){
			return "身份证号无效，请重新输入";
		}*/
        var res = __checkIdcard(idcard);
        if (res) {
            return '';
        }
        return "身份证号无效，请重新输入<a href='//ptlogin.4399.com/resource/howSetIdCard.html' target='_blank' title='不知道身份证号码？' class='ico_question'></a>";
    },

    CheckRealnameNew: function (realname) {
        // 判断全角的空白符
        realname = replaceAll(realname, '　', '');
        if (realname == '') {
            return '姓名不能为空';
            //return "例如：" + errTip;
        }
        var res = regRealName.test(realname);
        if (res) {
            return '';
        }
        return '姓名无效，请重新输入';
    },

    CheckIdcardNew: function (idcard, errTip) {
        // 判断全角的空白符
        idcard = replaceAll(idcard, '　', '');
        if (idcard == '') {
            return '身份证号不能为空';
        }
        var res = __checkIdcard(idcard);
        if (res) {
            return '';
        }
        return "身份证号无效，请重新输入<a href='//ptlogin.4399.com/resource/howSetIdCard.html' target='_blank' title='不知道身份证号码？' class='ico_question'></a>";
    },

    CheckAge: function (pid) {
        var len = (pid + '').length;
        if (len == 0) {
            return 0;
        } else {
            if (len != 15 && len != 18) {
                return 0;
            }
        }
        var strBirthday = '';
        if (len == 18) {
            strBirthday = pid.substr(6, 4) + '/' + pid.substr(10, 2) + '/' + pid.substr(12, 2);
        }
        if (len == 15) {
            strBirthday =
                '19' + pid.substr(6, 2) + '/' + pid.substr(8, 2) + '/' + pid.substr(10, 2);
        }

        var birthDate = new Date(strBirthday);
        var nowDateTime = new Date();
        var age = nowDateTime.getFullYear() - birthDate.getFullYear();

        if (
            nowDateTime.getMonth() < birthDate.getMonth() ||
            (nowDateTime.getMonth() == birthDate.getMonth() &&
                nowDateTime.getDate() < birthDate.getDate())
        ) {
            age--;
        }

        return age >= 18 ? true : false;
    },

    CheckEula: function (regEulaAgree) {
        if (regEulaAgree) return '';
        return '请阅读并同意4399相关协议';
    },

    CheckPhoneCaptcha: function (phoneCaptcha) {
        var res = regPhoneCaptcha.test(phoneCaptcha);
        if (res) return '';
        return '手机验证码必须为4或6个数字';
    },

    CheckNick: function (nick) {
        if (nick == '') return '请输入昵称';

        var len = nick.replace(/[^x00-xFF]/g, '**').length;
        if (len < 2 || len > 20) return '必须为1-10个汉字或20个字符';
        return '';
    }
};

/*验证密码是否相等*/
function verify_password(p1, p2, errDivId, allowBlank) {
    if (allowBlank && p1.value == '' && p2.value == '') return true;
    if (!setErr(errDivId, p1.value == p2.value ? null : '密码不一致', p2)) return false;
    if (!setErr(errDivId, Validaton.CheakPWD(p1.value, true), p1)) return false;

    return true;
}

/*手机短信验证码登录*/
function check_phone_login(errDivId, regEulaAgree) {
    var $secv = document.getElementById('j-sec').value;

    /*手机号*/
    var _sjV = document.getElementById('j-username');
    if (_sjV && !setErr(errDivId, Validaton.CheckPhone(_sjV.value))) return false;

    var _phonev = $secv == 1 ? encryptAES(_sjV.value) : _sjV.value;
    document.getElementById('j-sjphone').value = _phonev;

    /*验证码*/
    var captcha = document.getElementById('phoneCaptcha');
    if (captcha && !setErr(errDivId, Validaton.CheakCaptcha(captcha.value), captcha)) return false;

    if (!setErr(errDivId, Validaton.CheckEula(regEulaAgree.checked), regEulaAgree)) return false;
}

/*注册*/
function check_reg_new(errDivId, p1, p2, regEulaAgree) {
    var errDiv = document.getElementById(errDivId);
    if (errDiv) {
        errDiv.innerHTML = '';
    }

    var sendObj = document.getElementById('sendObj');
    if (sendObj) {
        input = document.getElementById('j-username');
        var checkstate = input.getAttribute('checkstate');
        if (checkstate && checkstate == 'err') {
            setErr(errDivId, '未获取手机验证码', input);
            return false;
        }
    }

    var captcha = document.getElementById('inputCaptcha');
    if (captcha && !setErr(errDivId, Validaton.CheakCaptcha(captcha.value), captcha)) return false;

    var inputs = document.getElementsByTagName('input');
    for (var i = 0; i < inputs.length; i++) {
        var input = inputs[i];
        var checkstate = input.getAttribute('checkstate');
        if (!checkstate || checkstate != 'err') continue;
        //input.focus();
        input.select();
        return false;
    }

    /*密码*/
    var _p1 = document.getElementById(p1),
        _p2 = document.getElementById(p2);
    if (_p1 && _p2) {
        var $secv = document.getElementById('j-sec').value;

        var _psdv = $secv == 1 ? encryptAES(_p1.value) : _p1.value;
        document.getElementById('j-psd').value = _psdv;

        var _psdvi = $secv == 1 ? encryptAES(_p2.value) : _p1.value;
        document.getElementById('j-psd-veri').value = _psdvi;
    }

    /*姓名、身份证*/
    if (
        document.getElementById('j-realname') &&
        document.getElementById('j-idcard') &&
        document.getElementById('j-xm-name') &&
        document.getElementById('j-xm-idcard')
    ) {
        var _xm = document.getElementById('j-realname').value,
            _idcard = document.getElementById('j-idcard').value;

        var _xmv = $secv == 1 ? encryptAES(_xm) : _xm;
        document.getElementById('j-xm-name').value = _xmv;

        var _idcardv = $secv == 1 ? encryptAES(_idcard) : _idcard;
        document.getElementById('j-xm-idcard').value = _idcardv;
    }

    /*手机注册*/
    if (isPhoneReg) {
        var _sjV = document.getElementById('j-username');
        var _phonev = $secv == 1 ? encryptAES(_sjV.value) : _sjV.value;
        document.getElementById('j-sjphone').value = _phonev;
    }

    if (_p1 && _p2) {
        if (!setErr(errDivId, _p1.value == _p2.value ? null : '两次密码不一致', _p2)) return false;
    }

    if (!setErr(errDivId, Validaton.CheckEula(regEulaAgree.checked), regEulaAgree)) return false;

    // var btn = document.getElementById("j-reg-submit-btn");
    // if(btn){
    //     btn.disabled = true;
    // }
}

/*注册*/
function check_reg(u, p1, p2, errDivId, captcha, email, realname, idcard, regEulaAgree, fFcm) {
    if (u && !setErr(errDivId, Validaton.CheakUsername(u.value, true), u)) return false;

    /*密码*/
    var _p1 = document.getElementById(p1),
        _p2 = document.getElementById(p2);

    var $secv = document.getElementById('j-sec').value;

    var _psdv = $secv == 1 ? encryptAES(_p1.value) : _p1.value;
    document.getElementById('j-psd').value = _psdv;

    var _psdvi = $secv == 1 ? encryptAES(_p2.value) : _p1.value;
    document.getElementById('j-psd-veri').value = _psdvi;

    if (!setErr(errDivId, _p1.value == _p2.value ? null : '密码不一致', _p2)) return false;

    if (!setErr(errDivId, Validaton.CheakPWD(_p1.value, true), _p1)) return false;

    //if(email && !setErr(errDivId, Validaton.CheckEmail(email.value), email))
    //return false;

    if (captcha && !setErr(errDivId, Validaton.CheakCaptcha(captcha.value), captcha)) return false;

    if (!fFcm && realname && !setErr(errDivId, Validaton.CheckRealname(realname.value), realname))
        return false;

    if (!fFcm && idcard && !setErr(errDivId, Validaton.CheckIdcard(idcard.value), idcard))
        return false;

    if (regEulaAgree && !setErr(errDivId, Validaton.CheckEula(regEulaAgree.checked), regEulaAgree))
        return false;

    return true;
}

/*登陆*/
function check_login(u, p, c, errDivId) {
    if (!setErr(errDivId, Validaton.CheakUsername(u.value), u)) {
        return false;
    }

    /* 密文传输 */

    var _p = document.getElementById(p);
    var $secv = document.getElementById('j-sec').value;
    var _psdInit = $secv == 1 ? encryptAES(_p.value) : _p.value;
    document.getElementById('j-psd').value = _psdInit;

    if (_p && !setErr(errDivId, Validaton.CheakPWD(_p.value), _p)) {
        return false;
    }

    if (c && !setErr(errDivId, Validaton.CheakCaptcha(c.value), c)) {
        return false;
    }

    // var btn = document.getElementById('j-login-submit-btn');
    // if(btn){
    //     btn.disabled = true;
    // }

    return true;
}

function check_edit_nick(n, errDivId) {
    if (!setErr(errDivId, Validaton.CheckNick(n.value), n)) return false;

    return true;
}

function setErr(errDivId, errInfo, input) {
    if (!errInfo) return true;
    var errDiv = document.getElementById(errDivId);
    if (errDiv) errDiv.innerHTML = errInfo;
    if (input) {
        //input.focus();
        //input.select();
    }
    return false;
}

// 以下是在注册窗口中的检查，绑定时的自动生成账号可以根据这个进行修改

/*
 * 要在 input中定义 tip 和 err 属性 type 分为 'username','password','email'
 * isRegister是否是注册时的检查，对登录的检查会松一些.
 */
function checkInput(input, type, isRegister, errTip) {
    checkRes = '';
    var _showInputOk = true;
    if (type == 'username') checkRes = Validaton.CheakUsername(input.value, isRegister);
    else if (type == 'password') {
        checkRes = Validaton.CheakPWD(input.value, isRegister);
    } else if (type == 'email') checkRes = Validaton.CheckEmail(input.value);
    else if (type == 'phone') {
        checkRes = Validaton.CheckPhone(input.value);
        _showInputOk = false;
    } else if (type == 'realname') {
        checkRes = Validaton.CheckRealnameNew(input.value, errTip);
    } else if (type == 'idcard') {
        checkRes = Validaton.CheckIdcardNew(input.value, errTip);
    } else if (type == 'regEulaAgree') {
        checkRes = Validaton.CheckEula(input.checked);
    } else if (type == 'phoneCaptcha') {
        checkRes = Validaton.CheckPhoneCaptcha(input.value);
        _showInputOk = false;
    }

    // if (checkRes == -1) {
    // 	if (type == "realname" || type == "idcard") {
    // 		return false;
    // 	}
    // }

    if (checkRes) {
        showInputErr(input, checkRes);
        return false;
    } else {
        if (_showInputOk) showInputOk(input, type);
        return true;
    }
}

/* 只校验规则 */
function checkRuleInput(input, type) {
    if (input.value == '') {
        input.setAttribute('checkstate', 'ok');
        return true;
    }
    var checkRes = '';
    if (type == 'idcard') {
        var rs_idcard = __checkIdcard(input.value);
        if (!rs_idcard) {
            checkRes =
                "身份证号无效，请重新输入<a href='//ptlogin.4399.com/resource/howSetIdCard.html' target='_blank' title='不知道身份证号码？' class='ico_question'></a>";
        } else {
            checkRes = '';
        }
    }

    if (type == 'realname') {
        var rs_realname = regRealName.test(input.value);
        if (!rs_realname) {
            checkRes = '姓名无效，请重新输入';
        } else {
            checkRes = '';
        }
    }

    if (type == 'qq') {
        var rs_qq = regQq.test(input.value);
        if (!rs_qq) {
            checkRes = 'QQ号无效，请重新输入';
        } else {
            checkRes = '';
        }
    }

    if (type == 'phone') {
        var rs_phone = regPhone.test(input.value);
        if (!rs_phone) {
            checkRes = '手机号必须为11个数字';
        } else {
            checkRes = '';
        }
    }

    if (checkRes) {
        showInputErr(input, checkRes);
        return false;
    } else {
        input.setAttribute('checkstate', 'ok');
    }
}

function getInputTipSpan(input) {
    var spans = input.parentNode.getElementsByTagName('span');
    if (spans.length == 0) {
        span = document.createElement('span');
        input.parentNode.appendChild(span);
        spans = input.parentNode.getElementsByTagName('span');
    }
    return spans[0];
}

function showInputTip(input, _regMode) {
    if (_regMode && (_regMode.value == 'reg_phone' || _regMode.value == 'login_phone')) {
        var sendObjEle = document.getElementById('sendObj');
        if (sendObjEle) {
            sendObjEle.style.display = 'block';
        }
    }
    input.select();
    var span = getInputTipSpan(input);
    span.className = 'input_tip';
    span.innerHTML = input.getAttribute('tip');

    // todo:开关
    /*if( input.getAttribute('id') == "j-realname"){
		document.getElementById('j-idcanrd-name').className= "m_idcard_tip_view";
	}

	if( input.getAttribute('id') == "j-idcard"){
		document.getElementById('j-idcanrd-num').className= "m_idcard_tip_view";
	}*/
}

function throttle(method, delay, time) {
    var timeout,
        startTime = new Date();
    return function () {
        var context = this,
            args = arguments,
            curTime = new Date();
        clearTimeout(timeout);
        // 如果达到了规定的触发时间间隔，触发 handler
        if (curTime - startTime >= time) {
            method.apply(context, args);
            startTime = curTime;
            // 没达到触发间隔，重新设定定时器
        } else {
            timeout = setTimeout(function () {
                method.apply(context, args);
            }, delay);
        }
    };
}

function throttleBtn(method, time) {
    var lastExecTime = 0;

    return function () {
        var context = this,
            args = arguments,
            curTime = new Date().getTime();

        if (curTime - lastExecTime >= time) {
            method.apply(context, args);
            lastExecTime = curTime;
        }
        // 完全去掉 else 分支，不设置任何定时器
    };
}

function showInputErr(input, errInfo, mystate) {
    var checkstate = input.getAttribute('checkstate');
    if (checkstate) {
        if (!mystate) mystate = 'err';
        input.setAttribute('checkstate', mystate);
    }
    var span = getInputTipSpan(input);
    span.className = 'input_tip_err';

    if (errInfo) {
        span.innerHTML = errInfo;
        return;
    }
    var err = input.getAttribute('err');
    if (!err) err = input.getAttribute('tip');
    span.innerHTML = err;
}

function showInputOk(input, type) {
    var checkstate = input.getAttribute('checkstate');
    if (checkstate) input.setAttribute('checkstate', 'ok');
    // 姓名身份证校验正确不显示打勾
    if (type && (type === 'realname' || type === 'idcard')) {
        return;
    }
    var span = getInputTipSpan(input);
    span.className = 'input_tip_ok';
    span.innerHTML = '';
}

function verifyPwdEqual(verifyPwd, p2) {
    if (!verifyPwd.value) {
        showInputErr(verifyPwd, '请再次输入密码');
        return;
    }
    if (verifyPwd.value != p2.value) showInputErr(verifyPwd, '两次密码不一致');
    else showInputOk(verifyPwd);
}

function checkRegNick(input, appInput) {
    var formatOk = checkInput(input, 'nick', true);
    if (!formatOk) return;
    checkNickExist(input, appInput);
}

function checkRegUsername(input, appInput, regMode, checkPhoneFormat) {
    if (typeof checkPhoneFormat == 'undefined' || checkPhoneFormat == false) {
        if (regMode.value == 'reg_phone' || regMode.value == 'login_phone') {
            return;
        }
    }

    if (regMode.value == 'reg_email') {
        var ue_tip = document.getElementById('ue_tip');
        if (ue_tip.style.display == 'block') return;
        if (openQQEmailTipOnNeed(input.value)) return;
    }
    var formatOk = checkInput(input, 'username', true);
    if (!formatOk) return;
    checkUsernameExist(input, appInput, regMode);
}

// 触发blur时执行
function checkUsernameExist(input, appInput, regMode) {
    var val = input.value;
    Ajax().get(
        '/ptlogin/isExist.do?username=' +
            val +
            '&appId=' +
            appInput.value +
            '&regMode=' +
            regMode.value,
        function (txt) {
            if (txt == '0') showInputOk(input);
            else showInputErr(input, txt);
        }
    );
}

function checkEditNick(input, appInput) {
    formatOk = Validaton.CheckNick(input.value);
    if (formatOk != '') {
        showInputErr(input, formatOk);
        return;
    }
    checkNickExist(input, appInput);
}

function checkNickExist(input, appInput) {
    var val = encodeURIComponent(input.value);
    Ajax().get('/ptlogin/isExist.do?nick=' + val + '&appId=' + appInput.value, function (txt) {
        if (txt == '0') showInputOk(input);
        else showInputErr(input, txt);
    });
}

ajax_v = 1;

var Ajax = function (recv) {
    var aj = new Object();
    aj.recv = recv || 'HTML';

    aj.load = function () {
        var request = false;
        if (window.XMLHttpRequest) {
            request = new XMLHttpRequest();
            if (request.overrideMimeType) {
                request.overrideMimeType('text/xml');
            }
        } else if (window.ActiveXObject) {
            var versions = [
                'Microsoft.XMLHTTP',
                'MSXML.XMLHTTP',
                'Microsoft.XMLHTTP',
                'Msxml2.XMLHTTP.7.0',
                'Msxml2.XMLHTTP.6.0',
                'Msxml2.XMLHTTP.5.0',
                'Msxml2.XMLHTTP.4.0',
                'MSXML2.XMLHTTP.3.0',
                'MSXML2.XMLHTTP'
            ];
            for (var i = 0; i < versions.length; i++) {
                try {
                    request = new ActiveXObject(versions[i]);
                    if (request) {
                        return request;
                    }
                } catch (e) {}
            }
        }
        return request;
    };

    aj.xhr = aj.load();

    aj.process = function () {
        if (aj.xhr.readyState == 4 && aj.xhr.status == 200) {
            if (aj.recv == 'HTML') {
                aj.func(aj.xhr.responseText);
            } else if (aj.recv == 'XML') {
                try {
                    aj.func(aj.xhr.responseXML.lastChild.firstChild.nodeValue);
                } catch (e) {
                    aj.func('');
                }
            }
        }
    };

    aj.get = function (url, func, funcError) {
        aj.func = func;
        aj.xhr.onerror = funcError;
        aj.xhr.onreadystatechange = aj.process;
        var delay = 100;
        if (url.indexOf('?') <= 0) url += '?';
        else url += '&';
        url += 'v=' + ajax_v++;
        if (window.XMLHttpRequest) {
            setTimeout(function () {
                aj.xhr.open('GET', url);
                aj.xhr.send(null);
            }, delay);
        } else {
            setTimeout(function () {
                aj.xhr.open('GET', url, true);
                aj.xhr.send();
            }, delay);
        }
    };

    aj.post = function (url, data, func, funcError) {
        aj.func = func;
        aj.xhr.onerror = funcError;
        aj.xhr.onreadystatechange = aj.process;
        aj.xhr.open('POST', url);
        aj.xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
        aj.xhr.send(data);
    };

    return aj;
};

captchax = 1;
function UniLoginChangPIC(sessionId) {
    var div = document.getElementById('captcha');
    div.src =
        '//ptlogin.4399.com/ptlogin/captcha.do?captchaId=' + sessionId + '&xx=' + captchax++;
    var input = document.getElementById('inputCaptcha');
    input.focus();
    input.select();
}

/*public object YJ*/
var YJ = YJ || {};
YJ = {
    G: function (id) {
        return typeof id == 'string' ? document.getElementById(id) : id;
    },
    extend: function (destination, target) {
        for (var prop in target) {
            destination[prop] = target[prop];
        }
        return destination;
    },
    getEvent: function (e) {
        return e || window.event;
    },
    getTarget: function (e) {
        return e.target || e.srcElement;
    },
    on: function (otarget, otype, fn) {
        if (otarget.addEventListener) {
            otarget.addEventListener(otype, fn, false);
        } else if (otarget.attachEvent) {
            otarget.attachEvent('on' + otype, fn);
        } else {
            otarget['on' + otype] = fn;
        }
    },
    each: function (object, callback, args) {
        var name,
            i = 0,
            length = object.length,
            isObj =
                length === undefined ||
                Object.prototype.toString.call(object) == '[object Function]';
        if (args) {
            if (isObj) {
                for (name in object) {
                    if (callback.apply(object[name], args === false)) {
                        break;
                    }
                }
            } else {
                for (; i < length; ) {
                    if (callback.apply(object[i++], args) === false) {
                        break;
                    }
                }
            }
        } else {
            if (isObj) {
                for (name in object) {
                    if (callback.call(object[name], name, object[name]) === false) {
                        break;
                    }
                }
            } else {
                for (; i < length; ) {
                    if (callback.call(object[i], i, object[i++]) === false) {
                        break;
                    }
                }
            }
        }
        return object;
    },
    stopPropagaton: function (e) {
        if (e.stopPropagaton) {
            e.stopPropagation();
        } else {
            e.cancelBubble = true;
        }
    },
    getCharCode: function (ev) {
        if (typeof ev.charCode == 'number') {
            return ev.charCode;
        } else {
            return ev.keyCode;
        }
    }
};

(function (win, undefined) {
    /*email suffix*/
    var suffixArr = new Array(
        '@163.com',
        '@qq.com',
        '@126.com',
        '@hotmail.com',
        '@gmail.com',
        '@sohu.com',
        '@sina.com'
    );

    /*emailAutoComplete*/
    function emailAutoComplete(arg) {
        this.opt = {
            subBox: 'ue_tip',
            tag: 'li',
            id: 'email',
            suffixArr: suffixArr,
            hoverClass: 'on'
        };
        this.setting = YJ.extend(this.opt, arg || {});
        this.curNum = 0;
        this.configValue = {
            _emailId: null,
            _subBoxId: null
        };
        if (!(this instanceof emailAutoComplete)) {
            return new emailAutoComplete(arg);
        }
        this.init();
    }
    emailAutoComplete.prototype = {
        constructor: emailAutoComplete,
        tipBox: function (v, obj) {
            var that = this;
            that.display(that.configValue._subBoxId, 1);
            var _str = '<span  id="j_utype" class="utype">请选择邮箱类型:</span><ul id="j_ulist">';
            _str += '<li><a href="javascript:void(0)"  class="cur_val">' + v + '</a></li>';
            var e = v.indexOf('@');
            if (e == -1) {
                YJ.each(that.setting.suffixArr, function (k, o) {
                    _str +=
                        '<li><a href="javascript:void(0)" id="e' + k + '">' + v + o + '</a></li>';
                });
            } else {
                var _sh = v.substring(0, e),
                    _se = v.substring(e);
                YJ.each(that.setting.suffixArr, function (k, o) {
                    if (o.indexOf(_se) != -1) {
                        _str +=
                            '<li><a href="javascript:void(0)" id="e' +
                            k +
                            '">' +
                            _sh +
                            o +
                            '</a></li>';
                    }
                });
            }
            _str += '</ul>';
            that.configValue._subBoxId.innerHTML = _str;
        },
        dropList: function () {
            var that = this;
            var _li = that.configValue._subBoxId.getElementsByTagName(that.setting.tag),
                _len = _li.length;
            for (var i = _len - 1; i >= 0; i--) {
                _li[i].className = '';
            }
            if (_len > 1) {
                if (that.curNum > _len - 1) {
                    that.curNum = 1;
                }
                if (that.curNum < 0) {
                    that.curNum = _len - 1;
                }
                _li[that.curNum].className = that.setting.hoverClass;
            } else {
                that.curNum = 0;
            }
        },
        display: function (obj, flag) {
            if (flag == 1) {
                obj.style.display = 'block';
            } else {
                obj.style.display = 'none';
            }
        },
        getClick: function () {
            var that = this;
            var _children = YJ.G('j_ulist').getElementsByTagName('li');
            for (var i = _children.length - 1; i >= 0; i--) {
                _children[i].onmouseover = (function (j) {
                    return function () {
                        _children[j].className = that.setting.hoverClass;
                    };
                })(i);

                _children[i].onmouseout = (function (j) {
                    return function () {
                        _children[j].className = '';
                    };
                })(i);

                _children[i].onclick = (function (j) {
                    return function (e) {
                        if (_children[j].id != 'j_utype') {
                            that.configValue._emailId.value = /<a[^\/].*>(.*)<\/a>/gi.exec(
                                _children[j].innerHTML
                            )[1];
                            that.display(that.configValue._subBoxId, 0);

                            document.getElementById('j-username').focus();

                            var nickElement = document.getElementById('nick');
                            if (nickElement) {
                                document.getElementById('nick').focus();
                                document.getElementById('nick').select();
                            }
                        }
                    };
                })(i);
            }
        },
        getKey: function () {
            var that = this;
            YJ.on(document, 'keydown', function (e) {
                var _ev = YJ.getEvent(e);
                switch (_ev.keyCode) {
                    case 40:
                        that.curNum++;
                        that.dropList();
                        break;
                    case 38:
                        that.curNum--;
                        that.dropList();
                        break;
                    default:
                        break;
                }
            });
            YJ.on(that.configValue._emailId, 'keydown', function (e) {
                var _li = that.configValue._subBoxId.getElementsByTagName(that.setting.tag),
                    _ev = YJ.getEvent(e);
                if (_ev.keyCode == 13 || _ev.keyCode == 9) {
                    if (that.curNum > _li.length - 1) that.curNum = _li.length - 1;
                    this.value = /<a[^\/].*>(.*)<\/a>/gi.exec(_li[that.curNum].innerHTML)[1];
                    that.display(that.configValue._subBoxId, 0);
                    that.curNum = 1;
                }
            });
        },
        init: function () {
            var that = this;
            (that.configValue._emailId = YJ.G(that.setting.id)),
                (that.configValue._subBoxId = YJ.G(that.setting.subBox));

            YJ.on(that.configValue._emailId, 'keyup', function (e) {
                var _ev = YJ.getEvent(e);

                if (_ev.keyCode == 40 || _ev.keyCode == 38) {
                    return false;
                }
                if (this.value != '') {
                    if (
                        _ev.keyCode != 38 &&
                        _ev.keyCode != 40 &&
                        _ev.keyCode != 13 &&
                        _ev.keyCode != 27
                    ) {
                        var _inputVal = this.value;
                        that.tipBox(_inputVal, this);
                        that.getClick();
                    }
                } else {
                    that.display(that.configValue._subBoxId, 0);
                }
            });
            that.getKey();
            YJ.on(document, 'click', function () {
                that.display(that.configValue._subBoxId, 0);
            });
        }
    };
    win.emailAutoComplete = emailAutoComplete;
})(window);

var PopupView = PopupView || {};
PopupView = {
    tip: function (txt) {
        var pview = this;
        var div = document.getElementById('j-tip_popup');
        if (!div) {
            div = document.createElement('div');
            div.className = 'ucenter_tip_wrap';
            div.id = 'j-tip_popup';
            document.body.appendChild(div);
        }
        div.innerHTML = '<div class="ucenter_tip">' + txt + '</div>';

        setTimeout(function () {
            div.innerHTML = '';
        }, 1500);
    },
    /**
     * 微博引导
     */
    guidanceForWeibo: function () {
        var pview = this;
        var div = document.getElementById('j-guidanceForWeibo_popup');
        if (!div) {
            div = document.createElement('div');
            div.className = 'ucenter_dialog_wrap';
            div.id = 'j-guidanceForWeibo_popup';
            document.body.appendChild(div);
        }
        div.innerHTML =
            '<div class="ucenter_dialog guidanceForWeibo_dialog">' +
            '<a class="btn_close" id="j-btn_close"></a>' +
            '<div class="dialog_bd">' +
            '<div class="guidanceForWeibo_wrap">' +
            '<div class="guidanceForWeibo_text">' +
            '因微博服务受限，建议您：<br/>' +
            '1、扫描下方二维码下载[4399游戏盒] <br/>' +
            '2、通过[4399游戏盒]修改密码 <a href="//ptlogin.4399.com/resource/guidanceForWeibo.html" target="_blank">查看详细教程</a><br/>' +
            '3、使用账号+密码登录<br/>' +
            '遇到问题？联系<a href="https://u.4399.com/chat/im/zhkf/zcdl" target="_blank">在线客服></a>' +
            '</div>' +
            '<div class="guidanceForWeibo_qrcode">' +
            '<div class="qrcode_item">' +
            '<img src="//ptlogin.4399.com/resource/images/android_code.png"></img><p>4399游戏盒（安卓版）</p>' +
            '</div>' +
            '<div class="qrcode_split">' +
            '</div>' +
            '<div class="qrcode_item">' +
            '<img src="//ptlogin.4399.com/resource/images/ios_code.png"></img><p>4399游戏盒（苹果版）</p>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            '</div>' +
            "<div class='ucenter_dialog_mask' style='width: 100%; height: " +
            document.documentElement.scrollHeight +
            "px; position: fixed; left: 0px; top: 0px; z-index: 1989;'></div>";

        document.getElementById('j-btn_close').onclick = function () {
            document.body.removeChild(div);
        };

    },
    /**
     * 勾选协议
     */
    checkProtocal: function (confirmCallback) {
        var div = document.getElementById('j-checkProtocal_popup');
        if (!div) {
            div = document.createElement('div');
            div.className = 'ucenter_dialog_wrap';
            div.id = 'j-checkProtocal_popup';
            document.body.appendChild(div);
        }
        div.innerHTML =
            '<div class="ucenter_dialog checkProtocal_dialog">' +
            '<div class="dialog_hd">登录提示</div>' +
            '<div class="dialog_bd">' +
            '<p>登录需要您阅读并同意：</p>' +
            '<p><a class="ucenter_btn_link" href="https://ptlogin.4399.com/resource/protocol.html?type=1&aids=1,3,6,7" target="_blank">《用户协议》</a>和' +
            '<a class="ucenter_btn_link" href="https://ptlogin.4399.com/resource/protocol.html?type=2&aids=2,10" target="_blank">《隐私政策》</a></p>' +
            '</div>' +
            '<div class="dialog_ft">' +
            '<button class="ucenter_btn" id="j-btn_cancel">暂不</button>' +
            '<button class="ucenter_btn ucenter_btn_primary" id="j-btn_confirm">同意</button>' +
            '</div>' +
            '</div>' +
            "<div class='ucenter_dialog_mask' style='width: 100%; height: " +
            document.documentElement.scrollHeight +
            "px; position: fixed; left: 0px; top: 0px; z-index: 1989;'></div>";

        document.getElementById('j-btn_confirm').onclick = function () {
            confirmCallback();
            document.body.removeChild(div);
        };
        document.getElementById('j-btn_cancel').onclick = function () {
            document.body.removeChild(div);
        };
    }
};

var strategies = {
    isEmpty: function (value, errorMsg) {
        return value === '' ? errorMsg : void 0;
    },
    isNum: function (value, errorMsg) {
        return !/(^[1-9]\d*$)/.test(value) ? errorMsg : void 0;
    },
    maxLength: function (value, length, errorMsg) {
        return value > +length ? errorMsg : void 0;
    },
    isMoblie: function (value, errorMsg) {
        if (value == '') return void 0;

        return !/^0{0,1}(13[0-9]|15[7-9]|15[0-7]|18[0-9])[0-9]{8}$/.test(value) ? errorMsg : void 0;
    },
    isEmail: function (value, errorMsg) {
        if (value == '') return void 0;

        return !/^[a-z0-9]+([._\\-]*[a-z0-9])*@([a-z0-9]+[-a-z0-9]*[a-z0-9]+.){1,63}[a-z0-9]+$/.test(
            value
        )
            ? errorMsg
            : void 0;
    },
    isRealName: function (value, errorMsg) {
        return !regRealName.test(value) ? errorMsg : void 0;
    },
    isIdcard: function (value, errorMsg) {
        return !__checkIdcard(value) ? errorMsg : void 0;
    },
    imageFormat: function (value, errorMsg) {
        return !/.(jpg|jpeg|png|JPG|JPEG|PNG)$/.test(value) ? errorMsg : void 0;
    },
    maxSize: function (value, length, errorMsg) {
        return value / 1024 / 1024 > length ? errorMsg : void 0;
    },
    isIdPassport: function (value, errorMsg) {
        return !/^[a-zA-Z0-9]{5,18}$/.test(value) ? errorMsg : void 0;
    },
    isIdTaiwan: function (value, errorMsg) {
        return !/(^\d{8})$/.test(value) ? errorMsg : void 0;
    },
    isReturnHome: function (value, errorMsg) {
        return !/(H|M|h|m)(\d{8})$/.test(value) ? errorMsg : void 0;
    }
};
var validator = {
    cache: [],
    add: function (value, rules) {
        var _this = this;
        for (var i = 0; i < rules.length; i++) {
            (function (i) {
                var rule = rules[i];
                var _arr = rule.strategy.split(':');
                var strategy = _arr.shift();
                _arr.unshift(value);
                _arr.push(rule.errorMsg);
                _this.cache.push(function () {
                    return strategies[strategy].apply(_this, _arr);
                });
            })(i);
        }
        return this;
    },
    start: function () {
        for (var i = 0; i < this.cache.length; i++) {
            var errorMsg = this.cache[i]();
            if (errorMsg) {
                return errorMsg;
            }
        }
    }
};
var eventHandles = {
    initIFrameReady: function (divId) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.initIFrameReady', divId);
        } else {
            if (window.parent.UniLogin && window.parent.UniLogin.initIFrameReady) {
                window.parent.UniLogin.initIFrameReady(divId);
            }
        }
    },
    __errorCallback: function (error) {
        try {
            if (Messenger.shouldOpen) {
                msnger.emit('unionLoginProps.__errorCallback', error);
            } else {
                if (window.parent.unionLoginProps.__errorCallback)
                    window.parent.unionLoginProps.__errorCallback(error);
            }
        } catch (e) {}
    },
    toQzoneLogin: function (reinit) {
        PopupView.checkProtocal(function () {
            if (Messenger.shouldOpen) {
                msnger.emit('UniLogin.toQzoneLogin', reinit);
            } else {
                parent.window.UniLogin.toQzoneLogin(reinit);
            }
        });
    },
    checkProtocalToQzoneLogin: function (reinit){
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.checkProtocalToQzoneLogin', reinit);
        } else {
            parent.window.UniLogin.checkProtocalToQzoneLogin(reinit);
        }
    },
    toWeixinLogin: function (reinit) {
        PopupView.checkProtocal(function () {
            if (Messenger.shouldOpen) {
                msnger.emit('UniLogin.toWeixinLogin', reinit);
            } else {
                parent.window.UniLogin.toWeixinLogin(reinit);
            }
        });
    },
    checkProtocalToWeixinLogin: function (reinit){
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.checkProtocalToWeixinLogin', reinit);
        } else {
            parent.window.UniLogin.checkProtocalToWeixinLogin(reinit);
        }
    },
    showPopupPhoneLogin: function () {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupPhoneLogin');
        } else {
            parent.window.UniLogin.showPopupPhoneLogin();
        }
    },
    toWeiboLogin: function () {
        PopupView.guidanceForWeibo();
    },
    showPopupLogin: function (username, password, reinit) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupLogin', [username, password, reinit]);
        } else {
            parent.window.UniLogin.showPopupLogin(username, password, reinit);
        }
    },
    showPopupUsernameLogin: function (username, password, reinit) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupUsernameLogin', [username, password, reinit]);
        } else {
            parent.window.UniLogin.showPopupUsernameLogin(username, password, reinit);
        }
    },
    showPopupReg: function (reinit) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupReg', reinit);
        } else {
            parent.window.UniLogin.showPopupReg(reinit);
        }
    },
    showPopupUsernameReg: function (reinit) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupUsernameReg', reinit);
        } else {
            parent.window.UniLogin.showPopupUsernameReg(reinit);
        }
    },
    showPopupQrLogin: function (reinit) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showPopupQrLogin', reinit);
        } else {
            parent.window.UniLogin.showPopupQrLogin(reinit);
        }
    },
    showLoginError: function (errInfo) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.showLoginError', errInfo);
        } else {
            parent.window.UniLogin.showLoginError(errInfo);
        }
    },
    closePopupLoginDiv: function (reason, isAuthon, action) {
        if (Messenger.shouldOpen) {
            msnger.emit('closePopupLoginDiv', [reason, isAuthon, action]);
        } else {
            parent.window.closePopupLoginDiv(reason, isAuthon, action);
        }
    },
    defaultPostEditNick: function () {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.defaultPostEditNick');
        } else {
            parent.window.UniLogin.defaultPostEditNick();
        }
    },
    defaultPostLogin: function (isReg) {
        if (Messenger.shouldOpen) {
            msnger.emit('UniLogin.defaultPostLogin', isReg);
        } else {
            parent.window.UniLogin.defaultPostLogin(isReg);
        }
    },
    locationHref: function (url) {
        if (Messenger.shouldOpen) {
            msnger.emit('locationHref', url);
        } else {
            if (!url) url = parent.location.href;
            parent.location.href = url;
        }
    }
};
