import unittest

from contextlib import contextmanager, ExitStack
from test.support import catch_unraisable_exception, import_helper


# Skip this test if the _testcapi module isn't available.
_testcapi = import_helper.import_module('_testcapi')


class TestDictWatchers(unittest.TestCase):
    # types of watchers testcapimodule can add:
    EVENTS = 0   # appends dict events as strings to global event list
    ERROR = 1    # unconditionally sets and signals a RuntimeException
    SECOND = 2   # always appends "second" to global event list

    def add_watcher(self, kind=EVENTS):
        return _testcapi.add_dict_watcher(kind)

    def clear_watcher(self, watcher_id):
        _testcapi.clear_dict_watcher(watcher_id)

    @contextmanager
    def watcher(self, kind=EVENTS):
        wid = self.add_watcher(kind)
        try:
            yield wid
        finally:
            self.clear_watcher(wid)

    def assert_events(self, expected):
        actual = _testcapi.get_dict_watcher_events()
        self.assertEqual(actual, expected)

    def watch(self, wid, d):
        _testcapi.watch_dict(wid, d)

    def unwatch(self, wid, d):
        _testcapi.unwatch_dict(wid, d)

    def test_set_new_item(self):
        d = {}
        with self.watcher() as wid:
            self.watch(wid, d)
            d["foo"] = "bar"
            self.assert_events(["new:foo:bar"])

    def test_set_existing_item(self):
        d = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            d["foo"] = "baz"
            self.assert_events(["mod:foo:baz"])

    def test_clone(self):
        d = {}
        d2 = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            d.update(d2)
            self.assert_events(["clone"])

    def test_no_event_if_not_watched(self):
        d = {}
        with self.watcher() as wid:
            d["foo"] = "bar"
            self.assert_events([])

    def test_del(self):
        d = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            del d["foo"]
            self.assert_events(["del:foo"])

    def test_pop(self):
        d = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            d.pop("foo")
            self.assert_events(["del:foo"])

    def test_clear(self):
        d = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            d.clear()
            self.assert_events(["clear"])

    def test_dealloc(self):
        d = {"foo": "bar"}
        with self.watcher() as wid:
            self.watch(wid, d)
            del d
            self.assert_events(["dealloc"])

    def test_unwatch(self):
        d = {}
        with self.watcher() as wid:
            self.watch(wid, d)
            d["foo"] = "bar"
            self.unwatch(wid, d)
            d["hmm"] = "baz"
            self.assert_events(["new:foo:bar"])

    def test_error(self):
        d = {}
        with self.watcher(kind=self.ERROR) as wid:
            self.watch(wid, d)
            with catch_unraisable_exception() as cm:
                d["foo"] = "bar"
                self.assertIs(cm.unraisable.object, d)
                self.assertEqual(str(cm.unraisable.exc_value), "boom!")
            self.assert_events([])

    def test_two_watchers(self):
        d1 = {}
        d2 = {}
        with self.watcher() as wid1:
            with self.watcher(kind=self.SECOND) as wid2:
                self.watch(wid1, d1)
                self.watch(wid2, d2)
                d1["foo"] = "bar"
                d2["hmm"] = "baz"
                self.assert_events(["new:foo:bar", "second"])

    def test_watch_non_dict(self):
        with self.watcher() as wid:
            with self.assertRaisesRegex(ValueError, r"Cannot watch non-dictionary"):
                self.watch(wid, 1)

    def test_watch_out_of_range_watcher_id(self):
        d = {}
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID -1"):
            self.watch(-1, d)
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID 8"):
            self.watch(8, d)  # DICT_MAX_WATCHERS = 8

    def test_watch_unassigned_watcher_id(self):
        d = {}
        with self.assertRaisesRegex(ValueError, r"No dict watcher set for ID 1"):
            self.watch(1, d)

    def test_unwatch_non_dict(self):
        with self.watcher() as wid:
            with self.assertRaisesRegex(ValueError, r"Cannot watch non-dictionary"):
                self.unwatch(wid, 1)

    def test_unwatch_out_of_range_watcher_id(self):
        d = {}
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID -1"):
            self.unwatch(-1, d)
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID 8"):
            self.unwatch(8, d)  # DICT_MAX_WATCHERS = 8

    def test_unwatch_unassigned_watcher_id(self):
        d = {}
        with self.assertRaisesRegex(ValueError, r"No dict watcher set for ID 1"):
            self.unwatch(1, d)

    def test_clear_out_of_range_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID -1"):
            self.clear_watcher(-1)
        with self.assertRaisesRegex(ValueError, r"Invalid dict watcher ID 8"):
            self.clear_watcher(8)  # DICT_MAX_WATCHERS = 8

    def test_clear_unassigned_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"No dict watcher set for ID 1"):
            self.clear_watcher(1)


class TestTypeWatchers(unittest.TestCase):
    # types of watchers testcapimodule can add:
    TYPES = 0    # appends modified types to global event list
    ERROR = 1    # unconditionally sets and signals a RuntimeException
    WRAP = 2     # appends modified type wrapped in list to global event list

    # duplicating the C constant
    TYPE_MAX_WATCHERS = 8

    def add_watcher(self, kind=TYPES):
        return _testcapi.add_type_watcher(kind)

    def clear_watcher(self, watcher_id):
        _testcapi.clear_type_watcher(watcher_id)

    @contextmanager
    def watcher(self, kind=TYPES):
        wid = self.add_watcher(kind)
        try:
            yield wid
        finally:
            self.clear_watcher(wid)

    def assert_events(self, expected):
        actual = _testcapi.get_type_modified_events()
        self.assertEqual(actual, expected)

    def watch(self, wid, t):
        _testcapi.watch_type(wid, t)

    def unwatch(self, wid, t):
        _testcapi.unwatch_type(wid, t)

    def test_watch_type(self):
        class C: pass
        with self.watcher() as wid:
            self.watch(wid, C)
            C.foo = "bar"
            self.assert_events([C])

    def test_event_aggregation(self):
        class C: pass
        with self.watcher() as wid:
            self.watch(wid, C)
            C.foo = "bar"
            C.bar = "baz"
            # only one event registered for both modifications
            self.assert_events([C])

    def test_lookup_resets_aggregation(self):
        class C: pass
        with self.watcher() as wid:
            self.watch(wid, C)
            C.foo = "bar"
            # lookup resets type version tag
            self.assertEqual(C.foo, "bar")
            C.bar = "baz"
            # both events registered
            self.assert_events([C, C])

    def test_unwatch_type(self):
        class C: pass
        with self.watcher() as wid:
            self.watch(wid, C)
            C.foo = "bar"
            self.assertEqual(C.foo, "bar")
            self.assert_events([C])
            self.unwatch(wid, C)
            C.bar = "baz"
            self.assert_events([C])

    def test_clear_watcher(self):
        class C: pass
        # outer watcher is unused, it's just to keep events list alive
        with self.watcher() as _:
            with self.watcher() as wid:
                self.watch(wid, C)
                C.foo = "bar"
                self.assertEqual(C.foo, "bar")
                self.assert_events([C])
            C.bar = "baz"
            # Watcher on C has been cleared, no new event
            self.assert_events([C])

    def test_watch_type_subclass(self):
        class C: pass
        class D(C): pass
        with self.watcher() as wid:
            self.watch(wid, D)
            C.foo = "bar"
            self.assert_events([D])

    def test_error(self):
        class C: pass
        with self.watcher(kind=self.ERROR) as wid:
            self.watch(wid, C)
            with catch_unraisable_exception() as cm:
                C.foo = "bar"
                self.assertIs(cm.unraisable.object, C)
                self.assertEqual(str(cm.unraisable.exc_value), "boom!")
            self.assert_events([])

    def test_two_watchers(self):
        class C1: pass
        class C2: pass
        with self.watcher() as wid1:
            with self.watcher(kind=self.WRAP) as wid2:
                self.assertNotEqual(wid1, wid2)
                self.watch(wid1, C1)
                self.watch(wid2, C2)
                C1.foo = "bar"
                C2.hmm = "baz"
                self.assert_events([C1, [C2]])

    def test_watch_non_type(self):
        with self.watcher() as wid:
            with self.assertRaisesRegex(ValueError, r"Cannot watch non-type"):
                self.watch(wid, 1)

    def test_watch_out_of_range_watcher_id(self):
        class C: pass
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID -1"):
            self.watch(-1, C)
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID 8"):
            self.watch(self.TYPE_MAX_WATCHERS, C)

    def test_watch_unassigned_watcher_id(self):
        class C: pass
        with self.assertRaisesRegex(ValueError, r"No type watcher set for ID 1"):
            self.watch(1, C)

    def test_unwatch_non_type(self):
        with self.watcher() as wid:
            with self.assertRaisesRegex(ValueError, r"Cannot watch non-type"):
                self.unwatch(wid, 1)

    def test_unwatch_out_of_range_watcher_id(self):
        class C: pass
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID -1"):
            self.unwatch(-1, C)
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID 8"):
            self.unwatch(self.TYPE_MAX_WATCHERS, C)

    def test_unwatch_unassigned_watcher_id(self):
        class C: pass
        with self.assertRaisesRegex(ValueError, r"No type watcher set for ID 1"):
            self.unwatch(1, C)

    def test_clear_out_of_range_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID -1"):
            self.clear_watcher(-1)
        with self.assertRaisesRegex(ValueError, r"Invalid type watcher ID 8"):
            self.clear_watcher(self.TYPE_MAX_WATCHERS)

    def test_clear_unassigned_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"No type watcher set for ID 1"):
            self.clear_watcher(1)

    def test_no_more_ids_available(self):
        contexts = [self.watcher() for i in range(self.TYPE_MAX_WATCHERS)]
        with ExitStack() as stack:
            for ctx in contexts:
                stack.enter_context(ctx)
            with self.assertRaisesRegex(RuntimeError, r"no more type watcher IDs"):
                self.add_watcher()


class TestCodeObjectWatchers(unittest.TestCase):
    @contextmanager
    def code_watcher(self, which_watcher):
        wid = _testcapi.add_code_watcher(which_watcher)
        try:
            yield wid
        finally:
            _testcapi.clear_code_watcher(wid)

    def assert_event_counts(self, exp_created_0, exp_destroyed_0,
                            exp_created_1, exp_destroyed_1):
        self.assertEqual(
            exp_created_0, _testcapi.get_code_watcher_num_created_events(0))
        self.assertEqual(
            exp_destroyed_0, _testcapi.get_code_watcher_num_destroyed_events(0))
        self.assertEqual(
            exp_created_1, _testcapi.get_code_watcher_num_created_events(1))
        self.assertEqual(
            exp_destroyed_1, _testcapi.get_code_watcher_num_destroyed_events(1))

    def test_code_object_events_dispatched(self):
        # verify that all counts are zero before any watchers are registered
        self.assert_event_counts(0, 0, 0, 0)

        # verify that all counts remain zero when a code object is
        # created and destroyed with no watchers registered
        co1 = _testcapi.code_newempty("test_watchers", "dummy1", 0)
        self.assert_event_counts(0, 0, 0, 0)
        del co1
        self.assert_event_counts(0, 0, 0, 0)

        # verify counts are as expected when first watcher is registered
        with self.code_watcher(0):
            self.assert_event_counts(0, 0, 0, 0)
            co2 = _testcapi.code_newempty("test_watchers", "dummy2", 0)
            self.assert_event_counts(1, 0, 0, 0)
            del co2
            self.assert_event_counts(1, 1, 0, 0)

            # again with second watcher registered
            with self.code_watcher(1):
                self.assert_event_counts(1, 1, 0, 0)
                co3 = _testcapi.code_newempty("test_watchers", "dummy3", 0)
                self.assert_event_counts(2, 1, 1, 0)
                del co3
                self.assert_event_counts(2, 2, 1, 1)

        # verify counts remain as they were after both watchers are cleared
        co4 = _testcapi.code_newempty("test_watchers", "dummy4", 0)
        self.assert_event_counts(2, 2, 1, 1)
        del co4
        self.assert_event_counts(2, 2, 1, 1)

    def test_clear_out_of_range_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"Invalid code watcher ID -1"):
            _testcapi.clear_code_watcher(-1)
        with self.assertRaisesRegex(ValueError, r"Invalid code watcher ID 8"):
            _testcapi.clear_code_watcher(8)  # CODE_MAX_WATCHERS = 8

    def test_clear_unassigned_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"No code watcher set for ID 1"):
            _testcapi.clear_code_watcher(1)

    def test_allocate_too_many_watchers(self):
        with self.assertRaisesRegex(RuntimeError, r"no more code watcher IDs available"):
            _testcapi.allocate_too_many_code_watchers()


class TestFuncWatchers(unittest.TestCase):
    @contextmanager
    def add_watcher(self, func):
        wid = _testcapi.add_func_watcher(func)
        try:
            yield
        finally:
            _testcapi.clear_func_watcher(wid)

    def test_func_events_dispatched(self):
        events = []
        def watcher(*args):
            events.append(args)

        with self.add_watcher(watcher):
            def myfunc():
                pass
            self.assertIn((_testcapi.PYFUNC_EVENT_CREATE, myfunc, None), events)
            myfunc_id = id(myfunc)

            new_code = self.test_func_events_dispatched.__code__
            myfunc.__code__ = new_code
            self.assertIn((_testcapi.PYFUNC_EVENT_MODIFY_CODE, myfunc, new_code), events)

            new_defaults = (123,)
            myfunc.__defaults__ = new_defaults
            self.assertIn((_testcapi.PYFUNC_EVENT_MODIFY_DEFAULTS, myfunc, new_defaults), events)

            new_defaults = (456,)
            _testcapi.set_func_defaults_via_capi(myfunc, new_defaults)
            self.assertIn((_testcapi.PYFUNC_EVENT_MODIFY_DEFAULTS, myfunc, new_defaults), events)

            new_kwdefaults = {"self": 123}
            myfunc.__kwdefaults__ = new_kwdefaults
            self.assertIn((_testcapi.PYFUNC_EVENT_MODIFY_KWDEFAULTS, myfunc, new_kwdefaults), events)

            new_kwdefaults = {"self": 456}
            _testcapi.set_func_kwdefaults_via_capi(myfunc, new_kwdefaults)
            self.assertIn((_testcapi.PYFUNC_EVENT_MODIFY_KWDEFAULTS, myfunc, new_kwdefaults), events)

            # Clear events reference to func
            events = []
            del myfunc
            self.assertIn((_testcapi.PYFUNC_EVENT_DESTROY, myfunc_id, None), events)

    def test_multiple_watchers(self):
        events0 = []
        def first_watcher(*args):
            events0.append(args)

        events1 = []
        def second_watcher(*args):
            events1.append(args)

        with self.add_watcher(first_watcher):
            with self.add_watcher(second_watcher):
                def myfunc():
                    pass

                event = (_testcapi.PYFUNC_EVENT_CREATE, myfunc, None)
                self.assertIn(event, events0)
                self.assertIn(event, events1)

    def test_watcher_raises_error(self):
        class MyError(Exception):
            pass

        def watcher(*args):
            raise MyError("testing 123")

        with self.add_watcher(watcher):
            with catch_unraisable_exception() as cm:
                def myfunc():
                    pass

                self.assertIs(cm.unraisable.object, myfunc)
                self.assertIsInstance(cm.unraisable.exc_value, MyError)

    def test_clear_out_of_range_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"invalid func watcher ID -1"):
            _testcapi.clear_func_watcher(-1)
        with self.assertRaisesRegex(ValueError, r"invalid func watcher ID 8"):
            _testcapi.clear_func_watcher(8)  # FUNC_MAX_WATCHERS = 8

    def test_clear_unassigned_watcher_id(self):
        with self.assertRaisesRegex(ValueError, r"no func watcher set for ID 1"):
            _testcapi.clear_func_watcher(1)

    def test_allocate_too_many_watchers(self):
        with self.assertRaisesRegex(RuntimeError, r"no more func watcher IDs"):
            _testcapi.allocate_too_many_func_watchers()


if __name__ == "__main__":
    unittest.main()
