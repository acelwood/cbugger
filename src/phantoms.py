
compiler_phantoms = []
breakpoint_phantoms = []


def clear_all_phantoms(view, edit):
	global compiler_phantoms, breakpoint_phantoms
	
	clear_phantoms(view, edit, compiler_phantoms)
	clear_phantoms(view, edit, breakpoint_phantoms)

	compiler_phantoms = []
	breakpoint_phantoms = []


def clear_phantoms(view, edit, phantoms):
	for region in phantoms:
		view.erase(edit, region)

 
# stylesheet = '''
#     <style>
#         div.error-arrow {
#             border-top: 0.4rem solid transparent;
#             border-left: 0.5rem solid color(var(--redish) blend(var(--background) 30%));
#             width: 0;
#             height: 0;
#         }
#         div.error {
#             padding: 0.4rem 0 0.4rem 0.7rem;
#             margin: 0 0 0.2rem;
#             border-radius: 0 0.2rem 0.2rem 0.2rem;
#         }
#         div.error span.message {
#             padding-right: 0.7rem;
#         }
#         div.error a {
#             text-decoration: inherit;
#             padding: 0.35rem 0.7rem 0.45rem 0.8rem;
#             position: relative;
#             bottom: 0.05rem;
#             border-radius: 0 0.2rem 0.2rem 0;
#             font-weight: bold;
#         }
#         html.dark div.error a {
#             background-color: #00000018;
#         }
#         html.light div.error a {
#             background-color: #ffffff18;
#         }
#     </style>
# '''