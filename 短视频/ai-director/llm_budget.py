#!/usr/bin/env python3
"""Conservative local LLM request guard and auditable reservation ledger.

Not a provider billing guarantee. Requires user-approved cap, peak-price ceilings,
max calls, and output token cap; every *attempt* is reserved before dispatch.
Never retries uncertain timeouts, transport errors, HTTP 5xx or interrupted calls.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import fcntl
import math
from pathlib import Path
import time


class BudgetError(Exception):
    pass


class RetryableLLMError(Exception):
    """Known malformed or empty response, or definitive HTTP 429 rejection."""
    pass


# Documented 2026-10-11 peak CNY/M-token input cache-miss, output.
# Always recheck official prices before a live run; provider can change rates.
DEEPSEEK_PEAK_CNY = {"deepseek-flash": (2.0, 8.0), "deepseek-v4-pro": (9.0, 27.0)}


def peak_rates(model: str, base_url: str):
    if base_url.rstrip('/').lower() in {'https://api.deepseek.com', 'https://api.deepseek.com/v1'}:
        return DEEPSEEK_PEAK_CNY.get(model)
    return None


def _finite_positive(value, name):
    try:
        x = float(value)
    except (ValueError, TypeError):
        raise BudgetError(f"{name} 必须是正数") from None
    if not math.isfinite(x) or x <= 0:
        raise BudgetError(f"{name} 必须是有限正数")
    return x


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def _save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


class BudgetSession:
    """Single-process guard. Never call same job concurrently.

    A reservation intentionally stays charged in this ledger, even if a provider
    says no usage, to avoid accidental double-spend on failed calls and resumes.
    """
    def __init__(self, *, job, model, base_url, cap_cny, input_cny_m, output_cny_m,
                 max_calls=7, max_retries=0, max_output_tokens=16384):
        self.path=Path(job)/'api_usage.generated.json'
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock_fd=None
        lock_path=self.path.parent/'.api_usage.lock'
        self._lock_fd=open(lock_path,'a+',encoding='utf-8')
        try:
            fcntl.flock(self._lock_fd.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self._lock_fd.close()
            self._lock_fd=None
            raise BudgetError('该项目已经有另一个API导演任务正在运行，不能并行扣费') from None
        self.cap_cny=_finite_positive(cap_cny,'--max-cost-cny')
        self.input_cny_m=_finite_positive(input_cny_m,'--input-cny-per-million')
        self.output_cny_m=_finite_positive(output_cny_m,'--output-cny-per-million')
        if not isinstance(max_calls, int) or not 1 <= max_calls <= 25:
            raise BudgetError('--max-calls 应为1至25')
        if not isinstance(max_retries, int) or not 0 <= max_retries <= 2:
            raise BudgetError('--max-retries 应为0至2')
        if not isinstance(max_output_tokens, int) or not 256 <= max_output_tokens <= 32768:
            raise BudgetError('--max-output-tokens 应为256至32768')
        self.max_calls=max_calls
        self.max_retries=max_retries
        self.max_output_tokens=max_output_tokens
        self.model=model
        self.base_url=base_url
        expected=peak_rates(model,base_url)
        if expected:
            if self.input_cny_m < expected[0] or self.output_cny_m < expected[1]:
                raise BudgetError('模型估价不能低于 DeepSeek 官方高峰标准；请复核价格后使用更保守的单价')
        elif base_url.startswith('https://'):
            # A different provider's cost must be entered knowingly by user.
            if self.input_cny_m == 2.0 and self.output_cny_m == 8.0:
                raise BudgetError('第三方或未知模型需手动明确指定输入/输出最高每百万token单价，不能套用Flash默认价')
        if self.path.exists():
            self.data=json.loads(self.path.read_text(encoding='utf-8'))
            for k,val in [('model',model),('base_url',base_url),('input_cny_m',self.input_cny_m),('output_cny_m',self.output_cny_m),('max_output_tokens',max_output_tokens)]:
                if self.data.get(k)!=val:
                    raise BudgetError('续跑配置与现有费用账本不一致；拒绝混用模型、价格和输出上限')
            if self.cap_cny < self.reserved_cny()-1e-9:
                raise BudgetError('新预算低于之前已预留的调用费用')
            if self.cap_cny != self.data['cap_cny']:
                self.data.setdefault('cap_changes',[]).append({'time':_now(),'old':self.data['cap_cny'],'new':self.cap_cny})
                self.data['cap_cny']=self.cap_cny
            self.data['max_calls']=min(max_calls,25)
            self.data['max_retries']=max_retries
        else:
            self.data={'version':1,'created':_now(),'model':model,'base_url':base_url,
                      'cap_cny':self.cap_cny,'input_cny_m':self.input_cny_m,
                      'output_cny_m':self.output_cny_m,'max_calls':max_calls,
                      'max_retries':max_retries,'max_output_tokens':max_output_tokens,
                      'note':'本地保守预留估算，不等于供应商实际账单；调用超时不自动重试',
                      'attempts':[]}
        _save(self.path,self.data)

    def close(self):
        if self._lock_fd is not None:
            fcntl.flock(self._lock_fd.fileno(),fcntl.LOCK_UN)
            self._lock_fd.close()
            self._lock_fd=None

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    def reserved_cny(self):
        return sum(float(x['reserved_cny']) for x in self.data['attempts'])

    def reserve(self, stage, system, user):
        # UTF-8 bytes is a deliberately conservative proxy for most BPE tokenizers,
        # with safety overhead. It is NOT an exact tokenizer or provider guarantee.
        input_proxy=len((system+'\n'+user).encode('utf-8'))+1024
        estimate=(input_proxy*self.input_cny_m + self.max_output_tokens*self.output_cny_m)/1_000_000
        if len(self.data['attempts'])>=self.max_calls:
            raise BudgetError(f'模型调用次数已达上限 {self.max_calls}，请求已被阻止')
        if self.reserved_cny()+estimate>self.cap_cny+1e-9:
            raise BudgetError(f'预估预留费 ¥{self.reserved_cny()+estimate:.4f} 超过上限 ¥{self.cap_cny:.4f}；未发起本次请求')
        record={'id':len(self.data['attempts'])+1,'time':_now(),'stage':stage,
                'prompt_sha256':hashlib.sha256((system+'\n'+user).encode()).hexdigest(),
                'input_proxy_tokens':input_proxy,'output_token_cap':self.max_output_tokens,
                'reserved_cny':round(estimate,8),'state':'inflight_unknown_if_interrupted'}
        self.data['attempts'].append(record)
        _save(self.path,self.data)
        return record

    def complete(self, record, state, usage=None):
        record['state']=state
        record['finished_at']=_now()
        if isinstance(usage,dict):
            record['provider_usage']={k:usage.get(k) for k in ('prompt_tokens','completion_tokens','total_tokens') if isinstance(usage.get(k),int)}
        _save(self.path,self.data)

    def invoke(self, *, stage, system, user, caller):
        # Caller receives usage_hook callback for actual token reporting.
        # Existing mocks may simply return dict and not call hook.
        for retry in range(self.max_retries+1):
            record=self.reserve(stage,system,user)
            usage_holder={}
            def usage_hook(x):
                if isinstance(x,dict):usage_holder.update(x)
            try:
                output=caller(usage_hook)
            except RetryableLLMError:
                self.complete(record,'retryable_failure',usage_holder)
                if retry>=self.max_retries:
                    raise
                # 429/empty JSON retries consume a fresh reservation on next loop.
                # No unbounded waits or hidden retries.
                continue
            except Exception:
                # Network/timeout/5xx might have been billed. Never retry blindly.
                self.complete(record,'failure_or_unknown_charge',usage_holder)
                raise
            else:
                self.complete(record,'completed',usage_holder)
                return output
        raise BudgetError('超过允许的重试次数')